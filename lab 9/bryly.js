const hideAllShapeInputs = () => {
    document.querySelectorAll(".inputCon").forEach(div => {
        div.style.display = "none";
    });
    document.querySelectorAll(".shapeInput").forEach(input => {
        input.value = 0;
    });
};

const showShapeInputs = (event) => {
    hideAllShapeInputs();
    const selectedShape = event.target.value;

    switch (selectedShape) {
        case "cylinder":
        case "cone":
            document.getElementById("heightCon").style.display = "flex";
        case "sphere":
            document.getElementById("radiusCon").style.display = "flex";
            break;

        case "prism":
        case "pyramid":
            document.getElementById("baseAreaCon").style.display = "flex";
            document.getElementById("heightCon").style.display = "flex";
            break;

        case "cuboid":
            document.getElementById("bWidthCon").style.display = "flex";
            document.getElementById("cHeightCon").style.display = "flex";
        case "cube":
            document.getElementById("aLengthCon").style.display = "flex";
            break;
    }
};

const calculateResults = () => {
    const shape = document.getElementById("shapeSelect").value;
    const densityRadios = document.querySelectorAll('input[name="material"]');

    const resultsCon = document.getElementById("resultsTableCon");
    let resultHtml = "<table><tr><th colspan=\"2\">Wyniki obliczeń:</th></tr>";

    const selectedResults = Array.from(
            document.getElementById("resultsSelect").selectedOptions
        ).map(opt => opt.value);

    if (selectedResults.includes("volume") || selectedResults.includes("mass")) {
        let volume = 0;
        switch (shape) {
            case "cylinder": {
                const radius = parseFloat(document.getElementById("radius").value) || 0;
                const height = parseFloat(document.getElementById("height").value) || 0;
                volume = Math.PI * Math.pow(radius, 2) * height;
                break;
            }
            case "cone": {
                const radius = parseFloat(document.getElementById("radius").value) || 0;
                const height = parseFloat(document.getElementById("height").value) || 0;
                volume = (1 / 3) * Math.PI * Math.pow(radius, 2) * height;
                break;
            }
            case "sphere": {
                const radius = parseFloat(document.getElementById("radius").value) || 0;
                volume = (4 / 3) * Math.PI * Math.pow(radius, 3);
                break;
            }
            case "prism":
            case "pyramid": {
                const baseArea = parseFloat(document.getElementById("baseArea").value) || 0;
                const height = parseFloat(document.getElementById("height").value) || 0;
                volume = baseArea * height;
                if (shape === "pyramid") {
                    volume /= 3;
                }
                break;
            }
            case "cuboid": {
                const length = parseFloat(document.getElementById("length").value) || 0;
                const width = parseFloat(document.getElementById("width").value) || 0;
                const height = parseFloat(document.getElementById("cHeight").value) || 0;
                volume = length * width * height;
                break;
            }
            case "cube": {
                const length = parseFloat(document.getElementById("length").value) || 0;
                volume = Math.pow(length, 3);
                break;
            }
        }
        if (selectedResults.includes("volume")) {
            resultHtml += `<tr><td>Objętość:</td><td>${volume.toFixed(2)} cm³</td></tr>`;
        }
        if (selectedResults.includes("mass")) {
            let density = 0;
            densityRadios.forEach(radio => {
                if (radio.checked) {
                    if (radio.value === "material1") density = 7.85;
                    else if (radio.value === "material2") density = 2.70;
                    else if (radio.value === "material3") density = 0.60;
                    else if (radio.value === "other") {
                        const densityInput = document.querySelector(".densityInput");
                        density = parseFloat(densityInput.value) || 0;
                    }
                }
            });

            const mass = volume * density;
            resultHtml += `<tr><td>Masa:</td><td>${mass.toFixed(2)} g</td></tr>`;
        }
    }

    if (selectedResults.includes("surfaceArea")) {
        let surfaceArea = 0;
        switch (shape) {
            case "cube": {
                const length = parseFloat(document.getElementById("length").value) || 0;
                surfaceArea = 6 * Math.pow(length, 2);
                break;
            }
            case "cuboid": {
                const length = parseFloat(document.getElementById("length").value) || 0;
                const width = parseFloat(document.getElementById("width").value) || 0;
                const height = parseFloat(document.getElementById("cHeight").value) || 0;
                surfaceArea = 2 * (length * width + width * height + height * length);
                break;
            }
            case "sphere": {
                const radius = parseFloat(document.getElementById("radius").value) || 0;
                surfaceArea = 4 * Math.PI * Math.pow(radius, 2);
                break;
            }
            case "cylinder": {
                const radius = parseFloat(document.getElementById("radius").value) || 0;
                const height = parseFloat(document.getElementById("height").value) || 0;
                surfaceArea = 2 * Math.PI * radius * (height + radius);
                break;
            }
            case "cone": {
                const radius = parseFloat(document.getElementById("radius").value) || 0;
                const height = parseFloat(document.getElementById("height").value) || 0;
                const slantHeight = Math.sqrt(Math.pow(radius, 2) + Math.pow(height, 2));
                surfaceArea = Math.PI * radius * (radius + slantHeight);
                break;
            }
            case "prism": {
                const baseArea = parseFloat(document.getElementById("baseArea").value) || 0;
                const height = parseFloat(document.getElementById("height").value) || 0;
                const perimeter = parseFloat(prompt("Podaj obwód podstawy graniastosłupa") || 0);
                surfaceArea = 2 * baseArea + perimeter * height;
                break;
            }
            case "pyramid": {
                const baseArea = parseFloat(document.getElementById("baseArea").value) || 0;                
                const perimeter = parseFloat(prompt("Podaj obwód podstawy ostrosłupa") || 0);
                const slantHeight = parseFloat(prompt("Podaj wysokość ścianki bocznej ostrosłupa") || 0);
                surfaceArea = baseArea + (perimeter * slantHeight) / 2;
                break;
            }
        }
        resultHtml += `<tr><td>Pole powierzchni:</td><td>${typeof surfaceArea === "number" ? surfaceArea.toFixed(2) + " cm²" : surfaceArea}</td></tr>`;
    }

    resultHtml += "</table>";
    resultsCon.innerHTML = resultHtml;
};


document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("shapeSelect");
    select.addEventListener("change", showShapeInputs);
    showShapeInputs({ target: select });

    const densityInput = document.querySelector(".densityInput");
    const materialRadios = document.querySelectorAll('input[name="material"]');
    materialRadios.forEach(radio => {
        radio.addEventListener("change", (event) => {
            if (event.target.value === "other") {
                densityInput.disabled = false;
            } else {
                densityInput.disabled = true;
                densityInput.value = "";
            }
        });
    });

    shapeForm.addEventListener("submit", (event) => {
        event.preventDefault();
        calculateResults();
    });
});
