from flask import Flask, render_template, request, send_file
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
from io import BytesIO
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from PIL import Image
import os
import time
import threading
import shutil


app = Flask(__name__, static_url_path='/static')

# Function to generate modified link for Scribd
def generate_modified_link(original_link):
    if "/doc/" in original_link:
                modified_link = original_link.replace("/doc/", "/embeds/").rsplit('/', 1)[0] + "/content"
    elif "/document/" in original_link:
                modified_link = original_link.replace("/document/", "/embeds/").rsplit('/', 1)[0] + "/content"
    elif "/presentation/" in original_link:
                modified_link = original_link.replace("/presentation/", "/embeds/").rsplit('/', 1)[0] + "/content"
    else:
        modified_link = original_link

    # modified_link = modified_link.replace("%2F", "/", 4)  # Replace only the first 4 occurrences of "%2F" with "/"
    # # modified_link += "&title=" + title.replace(" ", "+")
    # modified_link += "&utm_source=scrfree&utm_medium=queue&utm_campaign=dl"
    return modified_link

# # Function to get title from Scribd link
# def get_title_from_link(link):
#     response = requests.get(link)
#     if response.status_code == 200:
#         soup = BeautifulSoup(response.text, 'html.parser')
#         title_element = soup.find('h1', class_='_2qs3tf')
#         if title_element:
#             return title_element.text.strip()
#     return None

# Function to fetch video from Numerade
def fetch_numeade_video(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        video_element = soup.find('video', {'class': 'video-js'})
        if video_element:
            poster_link = video_element.get('poster')
            if "ask_previews" in poster_link:
                modified_link = poster_link.replace("ask_previews", "ask_video").replace("_large.jpg", ".webm")
            elif "previews" in poster_link:
                modified_link = poster_link.replace("previews", "encoded").replace("_large.jpg", ".mp4")
            else:
                modified_link = poster_link
            return modified_link
        else:
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

# Function to fetch image from Freepik
def fetch_freepik_image(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        image_tag = soup.find('img', {'src': lambda x: x and x.startswith('https://img.freepik.com/')})

        if image_tag:
            image_url = image_tag.get('src').replace('/thumb/', '/download/')
            return image_url

    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def fetch_academia_link(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        download_link = soup.find('a', {'href': re.compile(r'^https://www.academia.edu/attachments')})
        if download_link:
            return unquote(download_link['href'])
        else:
            return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None
    
    
# Function to process the Slideshare URL and extract image links
def process_url(url):
    image_links = []
    total_pages = None  # Initialize total_pages variable

    # Send a GET request to the URL
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the total number of pages
        page_number_element = soup.find('span', {'data-cy': 'page-number'})
        if page_number_element:
            total_pages = int(re.search(r'of (\d+)', page_number_element.text).group(1))

            # Iterate through each page
            for page_num in range(1, total_pages + 1):
                # Construct the page URL
                page_url = url + f"/{page_num}"

                # Send a GET request to the page URL
                page_response = requests.get(page_url)
                if page_response.status_code == 200:
                    page_soup = BeautifulSoup(page_response.text, 'html.parser')

                    # Find all picture tags with class 'SlideImage_picture__a3aKk'
                    picture_tags = page_soup.find_all('picture', {'class': 'SlideImage_picture__a3aKk'})
                    for picture_tag in picture_tags:
                        # Find the source tags within the picture tag
                        source_tags = picture_tag.find_all('source', {'data-testid': 'slide-image-source'})
                        for source_tag in source_tags:
                            # Extract the srcset attribute
                            srcset = source_tag.get('srcset')
                            if srcset:
                                # Extract image links from srcset
                                links = re.findall(r'https?://[^\s,]+', srcset)
                                image_links.extend(links)

    return image_links, total_pages  # Return total_pages along with image_links

# Function to download images
def download_images(image_links, total_pages):
    downloaded_images = []
    index = 1
    for link in image_links:
        match = re.search(r'-(\d+)-2048.jpg', link)
        if match:
            page_num = int(match.group(1))
            filename = f'image{page_num}.jpg'
            response = requests.get(link)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                downloaded_images.append(filename)
                index += 1
    return downloaded_images

# Function to create PDF
def create_pdf(image_files, pdf_filename):
    c = canvas.Canvas(pdf_filename, pagesize=landscape(letter))

    for image_file in image_files:
        image_path = f"{os.getcwd()}/{image_file}"
        img = Image.open(image_path)
        img_width, img_height = img.size
        c.setPageSize((img_width, img_height))
        c.drawInlineImage(image_path, 0, 0)

        c.showPage()

    c.save()

# Custom sorting function for image filenames
def sort_images(image_file):
    match = re.search(r'image(\d+).jpg', image_file)
    if match:
        return int(match.group(1))
    return 0

def delete_images(image_files):
    for image_file in image_files:
        os.remove(image_file)
        
# Function to delete temporary directory
def delete_temp_dir(temp_dir):
    shutil.rmtree(temp_dir)
    
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_message():
    message = request.form['message']
    urls = re.findall(r'(https?://[^\s]+)', message)
    numeade_links = [url for url in urls if "www.numerade.com/" in url]
    coursehero_links = [url for url in urls if "www.coursehero.com/" in url]
    chegg_links = [url for url in urls if "www.chegg.com/" in url]
    scribd_links = [url for url in urls if re.match(r'https?://(?:www\.)?scribd\.com/(document|doc|presentation)/[0-9]+/.+', url)]
    freepik_links = [url for url in urls if "www.freepik.com/" in url]
    academia_links = [url for url in urls if "www.academia.edu/" in url]
    slideshare_links = [url for url in urls if "www.slideshare.net" in url]
    responses = []
    
    
    for url in slideshare_links:
        # Process the URL to extract image links
        image_links, total_pages = process_url(url)

        # Filter out links that contain '-1-2048.jpg'
        filtered_links = [link for link in image_links if '-1-2048.jpg' in link]

        # Modify links in filtered_links and send all modified links
        if filtered_links:
            modified_links_sent = set()  # Track modified links already sent
            for link in filtered_links:
                for page_num in range(1, total_pages + 1):
                    modified_link = link.replace('-1-', f'-{page_num}-')
                    if modified_link not in modified_links_sent:
                        modified_links_sent.add(modified_link)

            # Download images using modified links
            modified_downloaded_images = download_images(modified_links_sent, total_pages)

            # Create PDF if there are downloaded images
            if modified_downloaded_images:
                pdf_filename = 'slides.pdf'

                # Sort downloaded images
                modified_downloaded_images.sort(key=sort_images)

                create_pdf(modified_downloaded_images, pdf_filename)
                
                delete_images([os.path.join(os.getcwd(), image) for image in modified_downloaded_images])


                # Generate a unique ID for the temporary file
                temp_id = int(time.time())

                # Move the PDF file to a temporary directory
                temp_dir = os.path.join('temp', str(temp_id))
                os.makedirs(temp_dir, exist_ok=True)
                temp_pdf_filename = os.path.join(temp_dir, pdf_filename)
                os.rename(pdf_filename, temp_pdf_filename)

                # Schedule the temporary directory for deletion after 5 minutes
                def delete_temp_dir_wrapper(temp_dir):
                    time.sleep(300)  # Wait for 5 minutes
                    delete_temp_dir(temp_dir)

                delete_temp_dir_thread = threading.Thread(target=delete_temp_dir_wrapper, args=(temp_dir,))
                delete_temp_dir_thread.start()

                # Provide a download link to the temporary PDF file
                responses.append({
                    'question': url,
                    'answer': f'/download/{temp_id}'
                })

            else:
                responses.append({
                    'question': url,
                    'answer': 'No images found on the provided URL.'
                })
        else:
            responses.append({
                'question': url,
                'answer': 'No valid image links found on the provided URL.'
            })

    if not responses:
        responses.append({
            'question': 'No URLs found in the message.',
            'answer': ''
        })



    # Handling Scribd links
    for url in scribd_links:
        
        
        if True:
            modified_link = generate_modified_link(url)
            responses.append({
                'question': url,
                'answer': modified_link
            })
        else:
            responses.append({
                'question': url,
                'answer': 'Failed to fetch document title. Please check the Scribd link.'
            })

    # Handling Numerade links
    if numeade_links:  
        for url in numeade_links:
            video_link = fetch_numeade_video(url)
            if video_link:
                responses.append({
                    'question': url,
                    'answer': video_link
                })
            else:
                responses.append({
                    'question': url,
                    'answer': 'No video found for this question.'
                })

    # Handling Course Hero and Chegg links
    for url in coursehero_links + chegg_links:
        responses.append({
            'question': url,
            'answer': 'Purchase'
        })

    # Handling Freepik links
    for url in freepik_links:
        image_url = fetch_freepik_image(url)
        if image_url:
            responses.append({
                'question': url,
                'answer': image_url
            })
        else:
            responses.append({
                'question': url,
                'answer': 'Failed to fetch image from Freepik.'
            })

    # Handling academia links
    for url in academia_links:
        link = fetch_academia_link(url)
        if link:
            responses.append({
                'question': url,
                'answer': link
            })
        else:
            responses.append({
                'question': url,
                'answer': 'Failed to fetch document from Academia.'
            })
        # Signal that the response is ready
    response_ready = True if responses else False

    return render_template('index.html', responses=responses, response_ready=response_ready)


@app.route('/download/<temp_id>')
def download_pdf(temp_id):
    temp_dir = os.path.join('temp', str(temp_id))
    temp_pdf_filename = os.path.join(temp_dir, 'slides.pdf')
    if os.path.exists(temp_pdf_filename):
        return send_file(temp_pdf_filename, as_attachment=True)
    else:
        return 'Temporary file not found.'

if __name__ == '__main__':
    app.run(debug=True)
