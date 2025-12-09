const updateTimeSpan = () => {
    const now = new Date();
    const timeSpan = document.getElementById("timeSpan");
    timeSpan.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
}

document.addEventListener("DOMContentLoaded", () => {
    const bitcoinButton = document.getElementById("bitcoinButton");

    bitcoinButton.addEventListener("click", async () => {
        bitcoinButton.textContent = "Pobieranie...";
        try {
            const response = await fetch("https://api.diadata.org/v1/assetQuotation/Bitcoin/0x0000000000000000000000000000000000000000");
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            const price = data.Price;
            bitcoinButton.textContent = `Cena Bitcoin: ${price.toFixed(2)} USD`;
        }
        catch (error) {
            console.error("Error fetching Bitcoin price:", error);
            bitcoinButton.textContent = "Wystąpił błąd";
        }
    });

    updateTimeSpan();
    setInterval(updateTimeSpan, 1000);
});