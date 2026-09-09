// 🔐 BURAK REVIEW ADMIN AUTH
let csrfToken = sessionStorage.getItem("burak_review_csrf") || "";

async function checkAdminAuth() {
    try {
        const response = await fetch("/api/auth/me", {
            method: "GET",
            credentials: "same-origin",
            cache: "no-store"
        });

        if (!response.ok) {
            window.location.href = "/admin-login.html";
            return false;
        }

        const data = await response.json();

        if (!data.authenticated) {
            window.location.href = "/admin-login.html";
            return false;
        }

        csrfToken = sessionStorage.getItem("burak_review_csrf") || "";

        if (!csrfToken) {
            window.location.href = "/admin-login.html";
            return false;
        }

        return true;
    } catch (error) {
        console.error("Admin doğrulama hatası:", error);
        window.location.href = "/admin-login.html";
        return false;
    }
}

// 🔐 BURAK REVIEW ADMIN LOGOUT
const logoutButton = document.getElementById("logoutButton");

if (logoutButton) {
    logoutButton.addEventListener("click", async () => {
        try {
            const response = await fetch(
                "/api/auth/logout",
                {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "X-CSRF-Token": csrfToken
                    }
                }
            );

            sessionStorage.removeItem("burak_review_csrf");

            if (!response.ok) {
                console.error("Logout başarısız.");
            }

            window.location.href = "/admin-login.html";
        } catch (error) {
            console.error("Logout hatası:", error);
            sessionStorage.removeItem("burak_review_csrf");
            window.location.href = "/admin-login.html";
        }
    });
}

const form = document.getElementById("productForm");
const prosContainer = document.getElementById("prosContainer");
const consContainer = document.getElementById("consContainer");
const specsContainer = document.getElementById("specsContainer");

const addProButton = document.getElementById("addPro");
const addConButton = document.getElementById("addCon");
const addSpecButton = document.getElementById("addSpec");

const imageInput = document.getElementById("productImage");
const imagePreview = document.getElementById("imagePreview");
const message = document.getElementById("adminMessage");

let selectedImage = null;


function createSlug(text) {
    return text
        .toLowerCase()
        .trim()
        .replace(/ğ/g, "g")
        .replace(/ü/g, "u")
        .replace(/ş/g, "s")
        .replace(/ı/g, "i")
        .replace(/ö/g, "o")
        .replace(/ç/g, "c")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
}


function addPro() {
    const row = document.createElement("div");
    row.className = "dynamic-row";

    row.innerHTML = `
        <input
            type="text"
            class="pro-input"
            placeholder="Örn. Çok güçlü ses kalitesi"
        >
        <button
            type="button"
            class="remove-row"
            aria-label="Artıyı sil"
        >×</button>
    `;

    row.querySelector(".remove-row").addEventListener(
        "click",
        () => row.remove()
    );

    prosContainer.appendChild(row);
}


function addCon() {
    const row = document.createElement("div");
    row.className = "dynamic-row";

    row.innerHTML = `
        <input
            type="text"
            class="con-input"
            placeholder="Örn. Fiyatı yüksek"
        >
        <button
            type="button"
            class="remove-row"
            aria-label="Eksiyi sil"
        >×</button>
    `;

    row.querySelector(".remove-row").addEventListener(
        "click",
        () => row.remove()
    );

    consContainer.appendChild(row);
}


function addSpec() {
    const row = document.createElement("div");
    row.className = "spec-editor-row";

    row.innerHTML = `
        <input
            type="text"
            class="spec-name"
            placeholder="Örn. Bluetooth"
        >
        <input
            type="text"
            class="spec-value"
            placeholder="Örn. 5.3"
        >
        <button
            type="button"
            class="remove-row"
            aria-label="Özelliği sil"
        >×</button>
    `;

    row.querySelector(".remove-row").addEventListener(
        "click",
        () => row.remove()
    );

    specsContainer.appendChild(row);
}


imageInput.addEventListener("change", () => {
    const file = imageInput.files[0];

    if (!file) {
        selectedImage = null;
        imagePreview.innerHTML = "";
        return;
    }

    selectedImage = file;

    const reader = new FileReader();

    reader.onload = (event) => {
        imagePreview.innerHTML = `
            <img
                src="${event.target.result}"
                alt="Ürün önizleme"
            >
        `;
    };

    reader.readAsDataURL(file);
});


function collectProductData() {
    const pros = [
        ...document.querySelectorAll(".pro-input")
    ]
        .map(input => input.value.trim())
        .filter(Boolean);

    const cons = [
        ...document.querySelectorAll(".con-input")
    ]
        .map(input => input.value.trim())
        .filter(Boolean);

    const shouldBuy = document
        .getElementById("shouldBuy")
        .value
        .split("\n")
        .map(item => item.trim())
        .filter(Boolean);

    const shouldNotBuy = document
        .getElementById("shouldNotBuy")
        .value
        .split("\n")
        .map(item => item.trim())
        .filter(Boolean);

    const specs = {};

    document
        .querySelectorAll(".spec-editor-row")
        .forEach(row => {
            const name = row
                .querySelector(".spec-name")
                .value
                .trim();

            const value = row
                .querySelector(".spec-value")
                .value
                .trim();

            if (name && value) {
                specs[name] = value;
            }
        });

    const name = document
        .getElementById("productName")
        .value
        .trim();

    return {
        slug: createSlug(name),

        brand: document
            .getElementById("productBrand")
            .value
            .trim(),

        name,

        category: document
            .getElementById("productCategory")
            .value,

        image: selectedImage
            ? selectedImage.name
            : "",

        imageData: null,

        imageName: selectedImage
            ? selectedImage.name
            : "",

        rating: Number(
            document
                .getElementById("productRating")
                .value
        ),

        verdict: document
            .getElementById("productVerdict")
            .value
            .trim(),

        price: document
            .getElementById("productPrice")
            .value
            .trim(),

        description: document
            .getElementById("productDescription")
            .value
            .trim(),

        pros,
        cons,
        shouldBuy,
        shouldNotBuy,
        specs,

        finalVerdict: document
            .getElementById("finalVerdict")
            .value
            .trim()
    };
}


document
    .getElementById("previewProduct")
    .addEventListener("click", () => {

        const product = collectProductData();

        console.log(
            "🔥 ÜRÜN ÖNİZLEME:",
            product
        );

        message.textContent =
            "👀 Ürün verisi hazırlandı. Tarayıcı konsolunu kontrol edebilirsin.";

        message.classList.add("show");
    });


async function fileToDataURL(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = () => resolve(reader.result);
        reader.onerror = () =>
            reject(new Error("Fotoğraf okunamadı."));

        reader.readAsDataURL(file);
    });
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const product = collectProductData();

    if (selectedImage) {
        product.imageData =
            await fileToDataURL(selectedImage);
    }

    message.textContent =
        "⏳ Ürün kaydediliyor...";

    message.classList.add("show");

    try {
        const response = await fetch(
            "/api/products",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json",
                    "X-CSRF-Token":
                        csrfToken
                },

                body: JSON.stringify(product)
            }
        );

        const result =
            await response.json();

        if (!response.ok) {
            throw new Error(
                result.error ||
                "Ürün kaydedilemedi."
            );
        }

        console.log(
            "🚀 KAYDEDİLEN ÜRÜN:",
            result
        );

        message.textContent =
            "✅ Ürün başarıyla kaydedildi! Ürün ID: " +
            result.id;

        form.reset();

        selectedImage = null;
        imagePreview.innerHTML = "";

    } catch (error) {

        console.error(
            "❌ KAYIT HATASI:",
            error
        );

        message.textContent =
            "❌ Ürün kaydedilemedi: " +
            error.message;
    }
});


addProButton.addEventListener(
    "click",
    addPro
);

addConButton.addEventListener(
    "click",
    addCon
);

addSpecButton.addEventListener(
    "click",
    addSpec
);


addPro();
addPro();

addCon();
addCon();

addSpec();
addSpec();


console.log(
    "🔥 BURAK REVIEW ADMIN HAZIR"
);


document.addEventListener("DOMContentLoaded", () => {
    checkAdminAuth();
});
