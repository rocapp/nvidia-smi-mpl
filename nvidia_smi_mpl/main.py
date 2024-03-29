import os
import traceback
import logging
from datetime import datetime
from matplotlib.widgets import Button
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import click
import subprocess
import re
import matplotlib as mpl
import pandas as pd
from dataclasses import dataclass, asdict
from threading import Thread

mpl.use('GTK3Agg')  # Use GTK3 backend
plt.close('all')


@dataclass
class Data:
    value: float
    unit: str
    title: str = None


@dataclass
class GPU:
    name: str
    temp: Data
    power: Data
    memory: Data
    gpu_util: Data
    tstamp: datetime


@dataclass
class MetricsList:
    gpu_temp: list
    gpu_power: list
    gpu_memory: list
    gpu_util: list
    tstamp: list


MEM_UNITS = ('KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')

def add_vertical_line(fig, axs, events):
    """Add a vertical line across all subplots."""
    timestamp = events[-1]
    for ax in axs:
        ax.axvline(x=timestamp, color='r', linestyle='--')
        ax.text(ax.get_xlim()[1]*0.9, ax.get_ylim()[1]*0.9, timestamp.strftime('%H:%M:%S'),
                color='red', fontsize=8)

def get_mem_unit(mem):
    for unit in MEM_UNITS:
        if mem.endswith(unit):
            return unit
    raise ValueError('Unknown memory unit')


def parse_nvidia_smi_output(output):
    """
    Parse the output of nvidia-smi command to extract GPU information.

    Args:
    - output: str, the output of the nvidia-smi command

    Returns:
    - GPU object: contains information about the GPU such as name, temperature, power usage, memory usage, GPU utilization, and timestamp

    Raises:
    - ValueError: if the nvidia-smi output cannot be parsed
    """
    # Remove unwanted characters
    output = re.sub(r'\+--*', '', output)
    output = re.sub(r'\|', '', output)
    # Convert to list of lists
    lines = [row.split() for row in output.split('\n') if row]
    # get data from lines
    for i in range(2, len(lines)):
        if lines[i-1][0] == '0' and lines[i-2][0].count('=') > 3:
            mem_unit = get_mem_unit(lines[i][6])
            return GPU(
                name=lines[i-1][1],
                temp=Data(value=float(lines[i][1].replace(
                    'C', '')), unit='C', title='Temperature'),
                power=Data(value=float(lines[i][3].replace(
                    'W', '')), unit='W', title='Power Usage'),
                memory=Data(value=float(lines[i][6].replace(
                    mem_unit, '')), unit=mem_unit, title='Memory Usage'),
                gpu_util=Data(value=float(
                    lines[i][-2].replace('%', '')), unit='%', title='GPU Utilization'),
                tstamp=datetime.now()
            )
    raise ValueError('Could not parse nvidia-smi output')


def get_nvidia_smi_data():
    """
    Retrieves and returns data from the nvidia-smi command.
    """
    output = subprocess.check_output(['nvidia-smi'], text=True)
    data = parse_nvidia_smi_output(output)
    return data


def update_plots(axs, df):
    n = 15
    dTdt = (df['gpu_temp'].diff().tail(n).max() + df['gpu_temp'].diff().tail(n).min())
    axs[0].cla()
    axs[0].plot(df['gpu_temp'], label='Temperature (C)')
    axs[0].legend(loc='upper left')
    if hasattr(dTdt, 'iloc'):
        dTdt = dTdt.iloc[-1]
    axs[0].set_title(
        f"GPU Temp. {df.gpu_temp.iloc[-1]} (C)\n"
        f"dT/dt {dTdt:.2f} (C/m)\n"
        f"Last Updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    axs[1].cla()
    axs[1].plot(df['gpu_power'], label='Power Usage (W)')
    axs[1].legend(loc='upper left')

    axs[2].cla()
    axs[2].plot(df['gpu_memory'], label='Memory Usage (MiB)')
    axs[2].legend(loc='upper left')

    axs[3].cla()
    axs[3].plot(df['gpu_util'], label='GPU Utilization (%)')
    axs[3].legend(loc='upper left')

events = []  # List of events

@click.command()
@click.option('--interval', default=1, help='Update interval in seconds.')
@click.option('--log-level', default='INFO', help='Set the logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)')
@click.option('--export-video', type=click.Path(), default=None, help='Export the plot as a video (MP4) to the specified path.')
@click.option('--export-frames', type=click.Path(), default=None, help='Export individual frames as PNG files to the specified path.')
@click.option('--api', default=False, is_flag=True, help='Start the API server.')
@click.option('--address', default='127.0.0.1', help='The address to bind the API server to.')
@click.option('--port', default=9000, help='The port to bind the API server to.')
@click.option('--hide-plot', default=False, is_flag=True, help='Hide the plot window.')
def main(interval, log_level, export_video, export_frames, api, address, port, hide_plot):
    """Real-time NVIDIA GPU metrics visualizer."""
    # Configure logging
    logging.basicConfig(level=getattr(logging, log_level.upper()),
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info('Starting NVIDIA GPU metrics visualizer')

    # Initialize the API server
    if api:
        from nvidia_smi_mpl.server import setup_server
        Thread(target=setup_server, args=(address, port)).start()

    fig, axs = plt.subplots(nrows=4, ncols=1, sharex='all', figsize=(10, 8))
    plt.subplots_adjust(hspace=0.5)

    # Initialize metrics
    metrics = MetricsList([], [], [], [], [])

    # Callback for the button
    def on_click(event):
        events.append(metrics.tstamp[-1])
        logging.info('Added vertical line at %s', metrics.tstamp[-1])

    # get current date
    today = datetime.now().strftime('%Y-%m-%d')

    # Function to save frames
    def save_frames(fig, frame_dir, frame_num):
        if not os.path.exists(frame_dir):
            os.makedirs(frame_dir)
        frame_path = os.path.join(frame_dir, f'frame{frame_num:04d}.png')
        fig.savefig(frame_path)
    
    def export_video_func(ani, export_video):
        writer = animation.FFMpegWriter(fps=12, metadata=dict(artist='Robbie Capps + You!'), bitrate=1600)
        logging.info('Exporting video to %s', export_video)
        ani.save(export_video, writer=writer)

    # Add a button for adding vertical lines
    ax_button = plt.axes([0.81, 0.05, 0.1, 0.075])  # Adjust the position as needed
    btn = Button(ax_button, f'Event {len(events):02d}')
    btn.on_clicked(on_click)

    def update(frame):
        data = get_nvidia_smi_data()
        metrics.gpu_temp.append(data.temp.value)
        metrics.gpu_power.append(data.power.value)
        metrics.gpu_memory.append(data.memory.value)
        metrics.gpu_util.append(data.gpu_util.value)
        metrics.tstamp.append(data.tstamp)
        mdict = asdict(metrics)
        df = pd.DataFrame(mdict, columns=mdict.keys(), index=metrics.tstamp)
        update_plots(axs, df)
        if len(events) > 0:
            add_vertical_line(fig, axs, events)
            fig.canvas.draw()
        if export_frames:
            frame_dir = str(export_frames)
            if today not in frame_dir:
                frame_dir = os.path.join(frame_dir, today)
            save_frames(fig, frame_dir, frame)

    ani = animation.FuncAnimation(fig, update, interval=interval*1000, save_count=1000)

    if export_video:
        if '.mp4' not in export_video:
            export_video += '.mp4'
        # Start a thread to export the video
        # Thread(target=export_video_func, args=(ani, export_video)).start()
        export_video_func(ani, export_video)
    
    logging.info('Application started. Updating every %s seconds', interval)
    if not hide_plot:
        logging.info('Plot window visible. Press Ctrl+C to exit')
        plt.show()
    else:
        logging.info('Plot window hidden. Press Ctrl+C to exit')
        plt.gcf().set_visible(False)


if __name__ == '__main__':
    main()
