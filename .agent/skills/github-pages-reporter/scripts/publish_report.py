#!/usr/bin/env python3
import os
import shutil
import argparse
from datetime import datetime
import subprocess

def publish_report(report_path, title, category, subtitle="", is_html=False):
    repo_root = os.getcwd() # Assumption: running from MoNaVLA root
    docs_dir = os.path.join(repo_root, "docs")
    reports_dir = os.path.join(docs_dir, "reports")
    
    # 1. Copy Report File
    filename = os.path.basename(report_path)
    target_path = os.path.join(reports_dir, filename)
    shutil.copy2(report_path, target_path)
    print(f"Copied report to {target_path}")

    # 2. Update docs/index.html
    index_path = os.path.join(docs_dir, "index.html")
    with open(index_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Find the target category tag or fallback
    category_pattern = f'<!-- Category: {category} -->'
    if category_pattern not in html_content:
        # If category doesn't exist, use the top one as fallback
        category_pattern = '<!-- Category: Sensitivity Analysis -->'

    date_str = datetime.now().strftime("%Y.%m.%d")
    
    # Construct Card HTML
    link_url = f"reports/{filename}" if is_html else f"reports/viewer.html?file={filename}"
    card_html = f"""
      <div class="column is-one-third">
        <div class="card methodology-box" style="padding: 20px;">
          <div class="mb-2">
            <span class="tag is-primary">{date_str}</span>
            <span class="tag is-light is-info">{category}</span>
          </div>
          <p class="title is-5">{title}</p>
          <p class="subtitle is-6">{subtitle}</p>
          <a href="{link_url}" class="button is-small is-fullwidth is-outlined is-link">View Report</a>
        </div>
      </div>
"""
    # Insert card after the category header
    parts = html_content.split(category_pattern)
    if len(parts) >= 2:
        # Insert after the found pattern. 
        # We find the next </h4> or just after the pattern
        insert_marker = '</h4>'
        h4_parts = parts[1].split(insert_marker, 1)
        if len(h4_parts) == 2:
            new_html = parts[0] + category_pattern + h4_parts[0] + insert_marker + card_html + h4_parts[1]
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(new_html)
            print(f"Updated index.html with new card for {title}")
        else:
            print("Could not find insertion point marker (</h4>) after category tag.")
    else:
        print(f"Category tag {category_pattern} not found in index.html.")

    # 3. Git commit and push (optional/manual suggested for safety, but auto-running is asked)
    try:
        subprocess.run(["git", "add", "docs/"], check=True)
        # Use simple commit message
        subprocess.run(["git", "commit", "-m", f"Report: {title} ({date_str})"], check=True)
        # We need to know where we are pushing. Assuming origin main.
        # Check current branch.
        # subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Commited changes to Docs. Run 'git push origin main' to publish.")
    except Exception as e:
        print(f"Git operation failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, help="Path to report file (md or html)")
    parser.add_argument("--title", required=True, help="Title for the card")
    parser.add_argument("--category", default="V5 Progress", help="Category in index.html")
    parser.add_argument("--subtitle", default="", help="Subtitle for the card")
    parser.add_argument("--is_html", action="store_true", help="Set if the report is raw html")
    args = parser.parse_args()
    
    publish_report(args.report, args.title, args.category, args.subtitle, args.is_html)
