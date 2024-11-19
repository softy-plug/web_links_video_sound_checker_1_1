import os

# Install required packages via pip if not already installed
os.system("pip install selenium webdriver-manager python-ffmpeg")

input("Нажмите Enter для запуска программы")

import time
import subprocess
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Function to read URLs from a text file
def read_links_from_file(file_path):
    with open(file_path, 'r') as file:
        links = file.readlines()
    return [link.strip() for link in links]

# Initialize the WebDriver (Chrome in this case)
def init_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    service = ChromeService(executable_path=ChromeDriverManager().install())
    browser = webdriver.Chrome(service=service, options=options)
    return browser

# Function to check if a link is a valid .mp4 video file
def is_video_link(url):
    return url.lower().endswith('.mp4')

# Function to get the size of the video file
def get_file_size(url):
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=size', '-of', 'default=noprint_wrappers=1:nokey=1', url]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return int(result.stdout.strip())

# Function to check if the video loads successfully
def check_video_link(browser, url):
    try:
        browser.get(url)
        time.sleep(2)  # Wait for the page to load
        
        # Check if the video element is present
        video_elements = browser.find_elements(By.TAG_NAME, 'video')
        return bool(video_elements)  # Returns True if video element found

    except Exception as e:
        print(f"Error accessing {url}: {e}")
    return False  # Catch-all for other issues

# Function to extract audio level using FFmpeg
def get_audio_level(segment_file):
    command = [
        'ffmpeg', '-i', segment_file, 
        '-af', 'volumedetect', 
        '-f', 'null', '/dev/null'
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stderr
    return extract_volume_level(output)

# Function to extract volume level from FFmpeg output
def extract_volume_level(output):
    for line in output.split('\n'):
        if 'max_volume' in line:
            return line.split(':')[-1].strip()
    return "N/A"  # If volume level can't be determined

# Function to extract video segments
def extract_segments(url):
    segments = []
    base_name = url.split('/')[-1].split('.')[0]  # Extract base name
    # Define segment timings in seconds
    segment_timings = [30, 30 * 60 + 30, 59 * 60 + 30]  # [30s, 30m30s, 59m30s]
    
    for start in segment_timings:
        segment_file = f"{base_name}_segment_{start}.mp4"
        command = [
            'ffmpeg', '-ss', str(start), '-i', url,
            '-t', '10', '-c', 'copy', segment_file, '-y'
        ]
        subprocess.run(command)
        segments.append(segment_file)
    
    return segments

# Main function to check all links from the file
def main():
    links = read_links_from_file('links.txt')
    browser = init_browser()

    results = {}
    for link in links:
        if is_video_link(link):
            success = check_video_link(browser, link)
            results[link] = {'success': success, 'audio_levels': [], 'segment_files': [], 'warnings': []}

            if success:
                # Get the size of the video file
                file_size = get_file_size(link)  # Size in bytes
                size_mb = file_size / (1024 * 1024)  # Convert bytes to MB

                # Check file size conditions
                if size_mb < 40:
                    results[link]['warnings'].append("WARNING: Файл меньше 40 МБ.")
                elif "wr_" in os.path.basename(link):
                    if size_mb > 1024 or size_mb < 40:
                        results[link]['warnings'].append("WARNING: Файл больше 1 ГБ или меньше 40 МБ.")

                # Wait for 5 seconds to view the video
                browser.get(link)
                time.sleep(5)

                # Extract segments and check audio levels
                segment_files = extract_segments(link)
                results[link]['segment_files'] = segment_files

                for segment in segment_files:
                    audio_level = get_audio_level(segment)
                    results[link]['audio_levels'].append(audio_level)
                    print(f"Audio level for {segment}: {audio_level}")

                # Delete segment files after processing
                for segment in segment_files:
                    if os.path.exists(segment):
                        os.remove(segment)
            
            print(f"URL: {link} - {'Success' if success else 'Failed to load video'}")

        else:
            results[link] = {'success': False, 'audio_levels': [], 'segment_files': []}
            print(f"URL: {link} - Invalid video link (not .mp4)")

    browser.quit()

    # Write results to a file
    with open('results.txt', 'w') as result_file:
        for link, status in results.items():
            result_file.write(f"{link} - {'Success' if status['success'] else 'Failed to load video or invalid link'}\n")
            result_file.write(f"Audio Levels: {', '.join(status['audio_levels'])}\n")
            result_file.write(f"Segments: {', '.join(status['segment_files'])}\n")
            if status['warnings']:
                result_file.write(f"Warnings: {', '.join(status['warnings'])}\n")

if __name__ == "__main__":
    main()

input("Проверка ссылок завершена. Нажмите Enter для закрытия окна")

# softy_plug