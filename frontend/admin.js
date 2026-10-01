// 🔐 BURAK REVIEW ADMIN AUTH (Supabase Auth oturumu)
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
            await fetch("/api/auth/logout", {
                method: "POST",
                credentials: "same-origin"
            });
        } catch (error) {
            console.error("Logout hatası:", error);
        }

        window.location.href = "/admin-login.html";
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

const listContainer = document.getElementById("adminProductList");
const cancelEditButton = document.getElementById("cancelEdit");
const submitButton = form.querySelector('button[type="submit"]');

let selectedImage = null;
let editingId = null;


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


function addPro(value = "") {
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

    row.querySelector(".pro-input").value = value;

    row.querySelector(".remove-row").addEventListener(
        "click",
        () => row.remove()
    );

    prosContainer.appendChild(row);
}


function addCon(value = "") {
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

    row.querySelector(".con-input").value = value;

    row.querySelector(".remove-row").addEventListener(
        "click",
        () => row.remove()
    );

    consContainer.appendChild(row);
}


function addSpec(name = "", value = "") {
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

    row.querySelector(".spec-name").value = name;
    row.querySelector(".spec-value").value = value;

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
        imagePreview.innerHTML = "";
        const img = document.createElement("img");
        img.src = event.target.result;
        img.alt = "Ürün önizleme";
        imagePreview.appendChild(img);
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

        image: "",

        imageData: null,

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


function resetForm() {
    form.reset();

    selectedImage = null;
    imagePreview.innerHTML = "";

    prosContainer.innerHTML = "";
    consContainer.innerHTML = "";
    specsContainer.innerHTML = "";

    addPro();
    addPro();
    addCon();
    addCon();
    addSpec();
    addSpec();
}


function setEditing(product) {
    editingId = product.id;

    document.getElementById("productName").value = product.name || "";
    document.getElementById("productBrand").value = product.brand || "";
    document.getElementById("productCategory").value = product.category || "";
    document.getElementById("productRating").value = product.rating ?? "";
    document.getElementById("productPrice").value = product.price || "";
    document.getElementById("productDescription").value = product.description || "";
    document.getElementById("productVerdict").value = product.verdict || "";
    document.getElementById("finalVerdict").value = product.finalVerdict || "";

    document.getElementById("shouldBuy").value =
        (product.shouldBuy || []).join("\n");

    document.getElementById("shouldNotBuy").value =
        (product.shouldNotBuy || []).join("\n");

    prosContainer.innerHTML = "";
    (product.pros && product.pros.length ? product.pros : [""])
        .forEach(item => addPro(item));

    consContainer.innerHTML = "";
    (product.cons && product.cons.length ? product.cons : [""])
        .forEach(item => addCon(item));

    specsContainer.innerHTML = "";
    const specs = product.specs || {};
    const specEntries = Object.entries(specs);

    if (specEntries.length) {
        specEntries.forEach(([name, value]) => addSpec(name, value));
    } else {
        addSpec();
    }

    imagePreview.innerHTML = "";
    if (product.image) {
        const img = document.createElement("img");
        img.src = product.image;
        img.alt = "Ürün önizleme";
        imagePreview.appendChild(img);
    }

    submitButton.textContent = "💾 Değişiklikleri kaydet";
    cancelEditButton.style.display = "inline-flex";

    message.textContent = `✏️ Düzenleniyor: ${product.name}`;
    message.classList.add("show");

    window.scrollTo({ top: 0, behavior: "smooth" });
}


function exitEditMode() {
    editingId = null;
    resetForm();

    submitButton.textContent = "🚀 Ürünü hazırla";
    cancelEditButton.style.display = "none";

    message.classList.remove("show");
}


async function deleteProduct(product) {
    const confirmed = window.confirm(
        `"${product.name}" ürününü silmek istediğinize emin misiniz? Bu işlem geri alınamaz.`
    );

    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch("/api/products", {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json"
            },
            credentials: "same-origin",
            body: JSON.stringify({ id: product.id })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Ürün silinemedi.");
        }

        if (editingId === product.id) {
            exitEditMode();
        }

        message.textContent = "🗑️ Ürün silindi.";
        message.classList.add("show");

        await loadProducts();

    } catch (error) {
        console.error("❌ SİLME HATASI:", error);
        message.textContent = "❌ Ürün silinemedi: " + error.message;
        message.classList.add("show");
    }
}


function renderProductList(products) {
    listContainer.innerHTML = "";

    if (!products.length) {
        const empty = document.createElement("p");
        empty.className = "admin-list-empty";
        empty.textContent = "Henüz ürün yok.";
        listContainer.appendChild(empty);
        return;
    }

    products.forEach(product => {
        const row = document.createElement("div");
        row.className = "admin-list-row";

        const info = document.createElement("div");
        info.className = "admin-list-info";

        const title = document.createElement("strong");
        title.textContent = product.name;

        const meta = document.createElement("span");
        meta.textContent = `${product.brand} • ${product.category} • ${product.rating}/5`;

        info.appendChild(title);
        info.appendChild(meta);

        const actions = document.createElement("div");
        actions.className = "admin-list-actions";

        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "admin-secondary-btn";
        editButton.textContent = "Düzenle";
        editButton.addEventListener("click", () => setEditing(product));

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "admin-danger-btn";
        deleteButton.textContent = "Sil";
        deleteButton.addEventListener("click", () => deleteProduct(product));

        actions.appendChild(editButton);
        actions.appendChild(deleteButton);

        row.appendChild(info);
        row.appendChild(actions);

        listContainer.appendChild(row);
    });
}


async function loadProducts() {
    try {
        const response = await fetch("/api/products", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(`Ürünler alınamadı: ${response.status}`);
        }

        const products = await response.json();

        if (!Array.isArray(products)) {
            throw new Error("Ürün listesi geçersiz.");
        }

        renderProductList(products);

    } catch (error) {
        console.error("❌ ÜRÜN LİSTESİ HATASI:", error);
        listContainer.innerHTML = "";
        const empty = document.createElement("p");
        empty.className = "admin-list-empty";
        empty.textContent = "Ürünler yüklenemedi.";
        listContainer.appendChild(empty);
    }
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


cancelEditButton.addEventListener("click", exitEditMode);


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

    const wasEditing = Boolean(editingId);

    message.textContent =
        "⏳ Ürün kaydediliyor...";

    message.classList.add("show");

    try {
        if (editingId) {
            const deleteResponse = await fetch(
                "/api/products",
                {
                    method: "DELETE",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    credentials: "same-origin",
                    body: JSON.stringify({ id: editingId })
                }
            );

            if (!deleteResponse.ok) {
                const detail = await deleteResponse
                    .json()
                    .catch(() => ({}));
                throw new Error(
                    detail.error || "Güncelleme başarısız."
                );
            }
        }

        const response = await fetch(
            "/api/products",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                credentials: "same-origin",

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

        exitEditMode();

        message.textContent = wasEditing
            ? "✅ Ürün güncellendi."
            : "✅ Ürün başarıyla kaydedildi! Ürün ID: " + result.id;

        message.classList.add("show");

        await loadProducts();

    } catch (error) {

        console.error(
            "❌ KAYIT HATASI:",
            error
        );

        message.textContent =
            "❌ Ürün kaydedilemedi: " +
            error.message;

        message.classList.add("show");
    }
});


addProButton.addEventListener(
    "click",
    () => addPro()
);

addConButton.addEventListener(
    "click",
    () => addCon()
);

addSpecButton.addEventListener(
    "click",
    () => addSpec()
);


resetForm();


console.log(
    "🔥 BURAK REVIEW ADMIN HAZIR"
);


document.addEventListener("DOMContentLoaded", async () => {
    const ok = await checkAdminAuth();

    if (ok) {
        loadProducts();
    }
});
