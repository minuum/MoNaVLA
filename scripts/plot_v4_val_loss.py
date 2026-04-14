
import re
import matplotlib.pyplot as plt

def parse_logs(log_path):
    epochs = []
    val_losses = []
    
    # Pattern to match validation loss improvement
    # Example 1: Metric val/loss improved. New best score: 3.487
    # Example 2: Metric val/loss improved by 0.276 >= min_delta = 0.0. New best score: 1.851
    best_score_pattern = re.compile(r"New best score: ([\d\.]+)")
    
    epoch_pattern = re.compile(r"Epoch (\d+):")

    current_epoch = None
    
    with open(log_path, 'r') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        m_epoch = epoch_pattern.search(line)
        if m_epoch:
            current_epoch = int(m_epoch.group(1))
            
        if "New best score:" in line:
            m_loss = best_score_pattern.search(line)
            if m_loss:
                val_loss_str = m_loss.group(1).rstrip('.')
                val_loss = float(val_loss_str)
                if current_epoch is not None:
                    # If this loss is found during or after an epoch, assign it
                    if not epochs or epochs[-1] != current_epoch:
                        epochs.append(current_epoch)
                        val_losses.append(val_loss)
                    else:
                        # Update to the latest best for the same epoch (unlikely but safe)
                        val_losses[-1] = val_loss


                        
    return epochs, val_losses

def plot_loss(epochs, val_losses, output_path):
    plt.figure(figsize=(10, 6))
    plt.plot(epochs, val_losses, marker='o', linestyle='-', color='b', label='Validation Loss (Best)')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('V4 Model Training - Validation Loss Trend')
    plt.grid(True)
    plt.legend()
    # Annotate points
    for i, txt in enumerate(val_losses):
        plt.annotate(f"{txt:.3f}", (epochs[i], val_losses[i]), textcoords="offset points", xytext=(0,10), ha='center')
    
    plt.savefig(output_path)
    print(f"Graph saved to {output_path}")

if __name__ == "__main__":
    epochs, losses = parse_logs("train_v4.log")
    if epochs:
        plot_loss(epochs, losses, "v4_val_loss_graph.png")
    else:
        print("No validation loss data found in log.")
