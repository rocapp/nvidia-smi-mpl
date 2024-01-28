import click
import subprocess
import re
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime

# Function to parse nvidia-smi output
def parse_nvidia_smi_output(output):
    lines = output.split('\n')
    for line in lines:
        if 'MiB' in line and '%' in line:  # This line contains the data we want
            parts = line.split('|')
            temp_perf = parts[1].strip().split(' ')
            power = parts[2].strip().split(' ')[0]
            memory = parts[2].strip().split(' ')[2]
            gpu_util = parts[3].strip().split(' ')[0]
            return {
                'temp': int(temp_perf[0][:-1]),  # Remove 'C' and convert to int
                'power': int(re.findall(r'\d+', power)[0]),  # Extract number
                'memory': int(re.findall(r'\d+', memory)[0]),  # Extract number
                'gpu_util': int(gpu_util[:-1])  # Remove '%' and convert to int
            }

# Function to update plots
def update_plots(axs, temp_data, power_data, memory_data, gpu_util_data):
    axs[0].cla()
    axs[0].plot(temp_data, label='Temperature (C)')
    axs[0].legend(loc='upper left')
    axs[0].set_title(f"GPU Temperature at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    axs[1].cla()
    axs[1].plot(power_data, label='Power Usage (W)')
    axs[1].legend(loc='upper left')

    axs[2].cla()
    axs[2].plot(memory_data, label='Memory Usage (MiB)')
    axs[2].legend(loc='upper left')

    axs[3].cla()
    axs[3].plot(gpu_util_data, label='GPU Utilization (%)')
    axs[3].legend(loc='upper left')

# Main function for CLI
@click.command()
@click.option('--interval', default=1, help='Update interval in seconds.')
def main(interval):
    """Real-time NVIDIA GPU metrics visualizer."""
    fig, axs = plt.subplots(4, 1)
    plt.subplots_adjust(hspace=1)

    temp_data, power_data, memory_data, gpu_util_data = [], [], [], []

    def update(frame):
        output = subprocess.check_output(['nvidia-smi'], text=True)
        data = parse_nvidia_smi_output(output)
        
        temp_data.append(data['temp'])
        power_data.append(data['power'])
        memory_data.append(data['memory'])
        gpu_util_data.append(data['gpu_util'])

        update_plots(axs, temp_data, power_data, memory_data, gpu_util_data)

    ani = animation.FuncAnimation(fig, update, interval=interval*1000)
    plt.show()

if __name__ == '__main__':
    main()
