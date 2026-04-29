"""
NavRoboKosMos — instruction-conditioned Kosmos-2 backbone for navigation.

RoboKosMos의 subclass. 추가 사항:
- forward_continuous에서 lang_x word embedding mean을 추출
- _forward_action_head에서 instruction_emb kwarg로 act_head에 전달
- MobileVLAClassificationDecoder.forward의 instr_proj가 이 embedding을 받아
  LSTM input에 additive conditioning 적용

third_party/RoboVLMs 수정 불필요.
"""
import torch
from robovlms.model.backbone.robokosmos import RoboKosMos


class NavRoboKosMos(RoboKosMos):
    """RoboKosMos + explicit instruction conditioning via word-embedding mean."""

    def forward_continuous(self, vision_x, lang_x, attention_mask=None, text_embedding=None, **kwargs):
        """lang_x word embedding을 mean pool해 _instr_emb_cache에 저장 후 parent 호출.

        text_embedding: (bs, 1024) frozen Kosmos-2 text embeddings for Exp18
        """
        # [Exp18] If frozen text_embedding provided, use it directly
        if text_embedding is not None:
            self._instr_emb_cache = text_embedding
        elif lang_x is not None:
            # lang_x: (bs, text_len) — forward_continuous 진입 시점의 원본 shape
            instr_embeds = self.word_embedding(lang_x)          # (bs, text_len, embed_dim)
            # detach: instr_proj만 학습, word embedding gradient path 분리
            self._instr_emb_cache = instr_embeds.mean(dim=1).detach()  # (bs, embed_dim)
        else:
            self._instr_emb_cache = None

        return super().forward_continuous(
            vision_x, lang_x, attention_mask=attention_mask, **kwargs
        )

    def _forward_action_head(
        self, action_tokens, action_labels, action_mask, mode="train", **kwargs
    ):
        """캐시된 instruction embedding을 kwargs로 act_head에 전달."""
        instr_emb = getattr(self, "_instr_emb_cache", None)
        if instr_emb is not None:
            kwargs["instruction_emb"] = instr_emb
        return super()._forward_action_head(
            action_tokens, action_labels, action_mask, mode=mode, **kwargs
        )
