/* ========= CONFIG ========= */
/* This is the ONLY place folders/images are defined */

const photoFolders = {
    nature: ["1.jpg", "2.jpg"],
    travel: ["1.jpg"],
    family: ["1.jpg"]
};

/* ========= STATE ========= */

let activeFolders = new Set(Object.keys(photoFolders));
let photos = [];
let pageIndex = 0;
const PAGE_SIZE = 9;

/* ========= INIT ========= */

const grid = document.getElementById("galleryGrid");
const filterPanel = document.getElementById("filterPanel");

function buildPhotoList() {
    photos = [];
    for (const folder of activeFolders) {
        photoFolders[folder].forEach(file => {
            photos.push(`Attachments/photos/${folder}/${file}`);
        });
    }
}

function renderGrid() {
    grid.innerHTML = "";
    const start = pageIndex * PAGE_SIZE;
    const slice = photos.slice(start, start + PAGE_SIZE);

    slice.forEach(src => {
        const img = document.createElement("img");
        img.src = src;
        grid.appendChild(img);
    });
}

/* ========= FILTER ========= */

function buildFilter() {
    filterPanel.innerHTML = "";

    Object.keys(photoFolders).forEach(folder => {
        const label = document.createElement("label");
        const checkbox = document.createElement("input");

        checkbox.type = "checkbox";
        checkbox.checked = true;

        checkbox.addEventListener("change", () => {
            if (!checkbox.checked && activeFolders.size === 1) {
                checkbox.checked = true;
                return;
            }

            checkbox.checked
                ? activeFolders.add(folder)
                : activeFolders.delete(folder);

            pageIndex = 0;
            buildPhotoList();
            renderGrid();
        });

        label.appendChild(checkbox);
        label.append(" " + folder);
        filterPanel.appendChild(label);
    });
}

/* ========= NAVIGATION ========= */

document.querySelector(".left-arrow").onclick = () => {
    if (pageIndex > 0) {
        pageIndex--;
        renderGrid();
    }
};

document.querySelector(".right-arrow").onclick = () => {
    if ((pageIndex + 1) * PAGE_SIZE < photos.length) {
        pageIndex++;
        renderGrid();
    }
};

/* ========= START ========= */

buildFilter();
buildPhotoList();
renderGrid();
