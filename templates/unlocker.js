// Fetching functions using the Fetch API (replaces requests library)
async function fetchAndParse(url) {
    const response = await fetch(url);
    const htmlContent = await response.text();
    const parsedHTML = new DOMParser().parseFromString(htmlContent, 'text/html');
    return parsedHTML;
  }
  
  // Event listener for button click
  document.getElementById('unlockButton').addEventListener('click', async () => {
    const pastedLink = document.getElementById('numeradeLink').value;
  
    if (pastedLink.includes('www.numerade.com/')) {
      try {
        const parsedHTML = await fetchAndParse(pastedLink);
        const videoElement = parsedHTML.querySelector('video.video-js');
  
        if (videoElement) {
          const posterLink = videoElement.poster;
          let modifiedLink = posterLink;
  
          if (posterLink.includes('ask_previews')) {
            modifiedLink = posterLink.replace('ask_previews', 'ask_video').replace('_large.jpg', '.mp4');
          } else if (posterLink.includes('previews')) {
            modifiedLink = posterLink.replace('previews', 'encoded').replace('_large.jpg', '.mp4');
          }
  
          // Display the unlocked link on the HTML page (replace with Discord integration if needed)
          document.getElementById('result').textContent = `Unlocked Link: ${modifiedLink}`;
        } else {
          // Handle the case where the video element is not found
          document.getElementById('result').textContent = 'Video element not found on the page.';
        }
      } catch (error) {
        // Handle errors during fetching or parsing
        document.getElementById('result').textContent = 'An error occurred while processing the link.';
      }
    } else {
      document.getElementById('result').textContent = 'Please enter a valid Numerade link.';
    }
  });
  