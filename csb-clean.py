#!/usr/bin/env python3

import os
import subprocess
import json
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich import box

console = Console()

# ============== BANNER ==============
def show_banner():
    console.clear()
    
    banner = """
[bold red]   ██████╗███████╗██████╗ [/bold red]
[bold red]  ██╔════╝██╔════╝██╔══██╗[/bold red]
[bold red]  ██║     ███████╗██████╔╝[/bold red]
[bold red]  ██║     ╚════██║██╔══██╗[/bold red]
[bold red]  ╚██████╗███████║██████╔╝[/bold red]
[bold red]   ╚═════╝╚══════╝╚═════╝ [/bold red]
[bold red]                          [/bold red]
[bold red]  ██╗   ██╗██╗██████╗ ███████╗ ██████╗ [/bold red]
[bold red]  ██║   ██║██║██╔══██╗██╔════╝██╔═══██╗[/bold red]
[bold red]  ██║   ██║██║██║  ██║█████╗  ██║   ██║[/bold red]
[bold red]  ╚██╗ ██╔╝██║██║  ██║██╔══╝  ██║   ██║[/bold red]
[bold red]   ╚████╔╝ ██║██████╔╝███████╗╚██████╔╝[/bold red]
[bold red]    ╚═══╝  ╚═╝╚═════╝ ╚══════╝ ╚═════╝ [/bold red]
"""
    console.print(banner)
    
    panel = Panel(
        "[bold green]CSB VIDEO COMPRESSOR PRO v10.0[/bold green]\n"
        "[yellow]━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]\n"
        "[yellow]CSB TEAM[/yellow]\n"
        "[cyan]Cyber Solution Bangladesh[/cyan]\n"
        "[magenta]Masum Vai[/magenta]",
        border_style="bright_blue",
        padding=(1, 10)
    )
    console.print(panel)
    console.print("")

# ============== GET VIDEO INFO ==============
def get_video_info(video_path):
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration,size',
            '-show_entries', 'stream=width,height,codec_name',
            '-of', 'json',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        duration = float(data['format'].get('duration', 0))
        size = int(data['format'].get('size', 0)) / (1024 * 1024)
        
        width, height, codec = 0, 0, "Unknown"
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                width = int(stream.get('width', 0))
                height = int(stream.get('height', 0))
                codec = stream.get('codec_name', 'Unknown')
                break
        
        return {
            'duration': duration,
            'size_mb': round(size, 2),
            'width': width,
            'height': height,
            'codec': codec
        }
    except:
        return None

# ============== COMPRESS VIDEO ==============
def compress_video(input_path, target_mb, output_path):
    console.print("[yellow]Compressing... Please wait[/yellow]")
    
    info = get_video_info(input_path)
    if not info or info['duration'] <= 0:
        console.print("[red]Failed to get video duration![/red]")
        return False
    
    duration = info['duration']
    bitrate = int((target_mb * 8192) / duration)
    if bitrate < 50:
        bitrate = 50
    if bitrate > 8000:
        bitrate = 8000
    
    console.print(f"[cyan]Target bitrate: {bitrate} kbps[/cyan]")
    
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-c:v', 'libx264',
        '-b:v', f'{bitrate}k',
        '-preset', 'fast',
        '-c:a', 'aac',
        '-b:a', '64k',
        '-movflags', '+faststart',
        '-y',
        output_path
    ]
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            bufsize=1
        )
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Encoding...", total=100)
            
            last_percent = 0
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                    
                if 'frame=' in output and 'fps=' in output:
                    try:
                        frame_match = output.split('frame=')[1].split()[0] if 'frame=' in output else None
                        if frame_match and frame_match.isdigit():
                            frame = int(frame_match)
                            fps_match = output.split('fps=')[1].split()[0] if 'fps=' in output else None
                            if fps_match and fps_match.replace('.', '').isdigit():
                                fps = float(fps_match)
                                if fps > 0:
                                    estimated_total = duration * fps
                                    percent = min(100, int((frame / estimated_total) * 100))
                                    if percent > last_percent:
                                        progress.update(task, completed=percent)
                                        last_percent = percent
                    except:
                        pass
        
        process.wait()
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1024 * 1024:
            return True
        else:
            console.print("[yellow]Retrying with slower preset...[/yellow]")
            cmd2 = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',
                '-b:v', f'{bitrate}k',
                '-preset', 'medium',
                '-c:a', 'aac',
                '-b:a', '64k',
                '-movflags', '+faststart',
                '-y',
                output_path
            ]
            subprocess.run(cmd2, capture_output=True, text=True, check=False)
            return os.path.exists(output_path)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False

# ============== FIND VIDEOS ==============
def find_videos():
    console.print("[cyan]Searching for videos...[/cyan]")
    
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.3gp', '.m4v']
    videos = []
    
    camera_path = "/storage/emulated/0/DCIM/Camera/"
    if os.path.exists(camera_path):
        for file in os.listdir(camera_path):
            if any(file.lower().endswith(ext) for ext in video_extensions):
                full_path = os.path.join(camera_path, file)
                try:
                    if os.path.getsize(full_path) > 1024 * 1024:
                        videos.append(full_path)
                except:
                    pass
    
    search_paths = [
        "/storage/emulated/0/Download/",
        "/storage/emulated/0/Movies/",
        "/storage/emulated/0/WhatsApp/Media/WhatsApp Video/",
        "/storage/emulated/0/"
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        full_path = os.path.join(root, file)
                        if full_path not in videos:
                            try:
                                if os.path.getsize(full_path) > 1024 * 1024:
                                    videos.append(full_path)
                            except:
                                pass
                        if len(videos) >= 30:
                            break
                if len(videos) >= 30:
                    break
        if len(videos) >= 30:
            break
    
    return videos

# ============== MAIN ==============
def main():
    show_banner()
    
    console.print("[bold yellow]Select video:[/bold yellow]")
    console.print("[green] 1) Enter path manually[/green]")
    console.print("[cyan] 2) Select from list[/cyan]")
    
    choice = Prompt.ask("[bold green]Option (1/2)[/bold green]", default="1")
    
    if choice == "1":
        video_path = Prompt.ask("[bold green]Enter video path[/bold green]")
        video_path = video_path.strip()
        
        if not os.path.exists(video_path):
            console.print(f"[red]File not found: {video_path}[/red]")
            return
        
        input_video = video_path
        
    else:
        videos = find_videos()
        
        if not videos:
            console.print("[red]No videos found![/red]")
            return
        
        console.print(f"[green]Found {len(videos)} videos[/green]\n")
        
        table = Table(title="Video List", border_style="bright_blue")
        table.add_column("#", style="yellow", width=6)
        table.add_column("File Name", style="cyan", width=40)
        table.add_column("Size (MB)", style="green", width=12)
        table.add_column("Resolution", style="magenta", width=15)
        
        for i, video in enumerate(videos, 1):
            info = get_video_info(video)
            name = os.path.basename(video)
            size = info['size_mb'] if info else 0
            if info and info['width'] > 0 and info['height'] > 0:
                res = f"{info['width']}x{info['height']}"
            else:
                res = "Unknown"
            table.add_row(str(i), name, str(size), res)
        
        console.print(table)
        console.print("")
        
        num = IntPrompt.ask("[bold green]Enter video number[/bold green]", default=1)
        
        if 1 <= num <= len(videos):
            input_video = videos[num - 1]
        else:
            console.print("[red]Invalid number![/red]")
            return
    
    console.print("")
    info = get_video_info(input_video)
    if info:
        table = Table(title="Video Information", border_style="bright_green")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")
        table.add_row("File", os.path.basename(input_video))
        table.add_row("Size", f"{info['size_mb']} MB")
        table.add_row("Duration", f"{int(info['duration']//60)}m {int(info['duration']%60)}s")
        if info['width'] > 0 and info['height'] > 0:
            table.add_row("Resolution", f"{info['width']}x{info['height']}")
        console.print(table)
    
    console.print("\n[bold white]Select target size:[/bold white]")
    console.print("[green] 1) 500 MB[/green]")
    console.print("[blue] 2) 750 MB[/blue]")
    console.print("[magenta] 3) 1000 MB (1 GB)[/magenta]")
    console.print("[red] 4) 100 MB[/red]")
    console.print("[cyan] 5) 50 MB[/cyan]")
    console.print("[green] 6) 10 MB[/green]")
    console.print("[yellow] 7) 1 MB (Smallest)[/yellow]")
    console.print("[white] 8) Custom (Enter MB manually)[/white]")
    
    option = Prompt.ask("[bold green]Option (1-8)[/bold green]", default="1")
    
    target_sizes = {
        '1': 500, '2': 750, '3': 1000,
        '4': 100, '5': 50, '6': 10, '7': 1
    }
    
    if option in target_sizes:
        target_mb = target_sizes[option]
    elif option == '8':
        target_mb = IntPrompt.ask("[bold yellow]Enter target MB[/bold yellow]")
        if target_mb < 1:
            console.print("[red]Must be at least 1 MB![/red]")
            return
    else:
        console.print("[red]Invalid! Using 500 MB[/red]")
        target_mb = 500
    
    output_dir = os.path.dirname(input_video)
    base_name = os.path.splitext(os.path.basename(input_video))[0]
    output_file = os.path.join(output_dir, f"{base_name}_{target_mb}mb.mp4")
    
    console.print("")
    console.print(f"[cyan]Input: {os.path.basename(input_video)}[/cyan]")
    console.print(f"[green]Target: {target_mb} MB[/green]")
    console.print(f"[yellow]Output: {os.path.basename(output_file)}[/yellow]")
    
    confirm = Prompt.ask("[bold red]Start compression? (y/n)[/bold red]", default="y")
    if confirm.lower() != 'y':
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    start_time = time.time()
    success = compress_video(input_video, target_mb, output_file)
    elapsed_time = time.time() - start_time
    
    console.print("")
    if success and os.path.exists(output_file):
        new_size = os.path.getsize(output_file) / (1024 * 1024)
        
        result_panel = Panel(
            f"[bold green]SUCCESSFULLY COMPRESSED![/bold green]\n"
            f"[cyan]File: {os.path.basename(output_file)}[/cyan]\n"
            f"[yellow]New Size: {round(new_size, 2)} MB[/yellow]\n"
            f"[green]Reduced: {round(((info['size_mb'] - new_size) / info['size_mb']) * 100, 1)}%[/green]\n"
            f"[dim]Time: {int(elapsed_time//60)}m {int(elapsed_time%60)}s[/dim]\n"
            f"[dim]Location: {os.path.dirname(output_file)}[/dim]\n\n"
            "[bold magenta]Thanks from CSB TEAM[/bold magenta]\n"
            "[cyan]Cyber Solution Bangladesh - Masum Vai[/cyan]",
            border_style="bright_green",
            padding=1
        )
        console.print(result_panel)
    else:
        console.print("[red]Compression failed![/red]")
        console.print("[yellow]Try a different file or smaller size.[/yellow]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
