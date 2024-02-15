// Copy text function
function copyTextById(textElementId) {
    const textElement = document.getElementById(textElementId);

    if (textElement) {
        const textToCopy = textElement.textContent;

        navigator.clipboard.writeText(textToCopy)
            .then(() => {
                alert('Text copied! Hit ENTER to Close');
            })
            .catch(err => {
                console.error('Failed to copy: ', err);
            });
    } else {
        console.error('Text element not found.');
    }
}