let products = [];

const params = new URLSearchParams(window.location.search);
const slug = params.get("urun");

const notFound = document.getElementById("productNotFound");
const content = document.getElementById("productContent");

function showNotFound() {
    content.style.display = "none";
    notFound.style.display = "block";

    const robots = document.querySelector('meta[name="robots"]');

    if (robots) {
        robots.setAttribute("content", "noindex, follow");
    }
}

function createStars(rating) {
    const rounded = Math.round(Number(rating) || 0);

    return (
        "★".repeat(rounded) +
        "☆".repeat(5 - rounded)
    );
}

function fillList(id, items) {
    const list = document.getElementById(id);

    list.innerHTML = "";

    (Array.isArray(items) ? items : []).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        list.appendChild(li);
    });
}

function setMeta(selector, content) {
    const element = document.querySelector(selector);

    if (element && content) {
        element.setAttribute("content", content);
    }
}

function setLink(rel, href) {
    const element = document.querySelector(`link[rel="${rel}"]`);

    if (element && href) {
        element.setAttribute("href", href);
    }
}

function absoluteUrl(value) {
    if (!value) {
        return "";
    }

    if (/^https?:\/\//i.test(value)) {
        return value;
    }

    return `${window.location.origin}/${String(value).replace(/^\/+/, "")}`;
}

function updateSeo(product) {
    const origin = window.location.origin;

    const canonical =
        `${origin}/product.html?urun=${encodeURIComponent(slug)}`;

    const title =
        `${product.name} İncelemesi | Burak Review`;

    const description = (
        product.description ||
        `${product.name} teknik özellikleri, artıları, eksileri ve Burak Review değerlendirmesi.`
    ).slice(0, 160);

    const image = absoluteUrl(product.image) || `${origin}/og-image.jpg`;

    document.title = title;

    setMeta('meta[name="description"]', description);
    setMeta('meta[property="og:title"]', title);
    setMeta('meta[property="og:description"]', description);
    setMeta('meta[property="og:url"]', canonical);
    setMeta('meta[property="og:image"]', image);
    setMeta('meta[property="og:image:alt"]', `${product.brand} ${product.name}`);
    setMeta('meta[name="twitter:title"]', title);
    setMeta('meta[name="twitter:description"]', description);
    setMeta('meta[name="twitter:image"]', image);

    setLink("canonical", canonical);
}

function injectStructuredData(product) {
    const origin = window.location.origin;

    const image = absoluteUrl(product.image);

    const specs =
        product.specs && typeof product.specs === "object"
            ? product.specs
            : {};

    const data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "description": product.description || undefined,
        "category": product.category || undefined,
        "url": `${origin}/product.html?urun=${encodeURIComponent(slug)}`,
        "brand": product.brand
            ? { "@type": "Brand", "name": product.brand }
            : undefined,
        "image": image ? [image] : undefined,
        "additionalProperty": Object.entries(specs).map(([name, value]) => ({
            "@type": "PropertyValue",
            "name": name,
            "value": String(value)
        }))
    };

    const rating = Number(product.rating);

    if (rating > 0) {
        data.review = {
            "@type": "Review",
            "reviewRating": {
                "@type": "Rating",
                "ratingValue": rating,
                "bestRating": 5,
                "worstRating": 0
            },
            "author": {
                "@type": "Organization",
                "name": "Burak Review"
            },
            "reviewBody":
                product.finalVerdict ||
                product.verdict ||
                undefined
        };
    }

    const script = document.createElement("script");

    script.type = "application/ld+json";
    script.textContent = JSON.stringify(data);

    document.head.appendChild(script);
}

async function loadProduct() {
    try {
        if (!slug) {
            showNotFound();
            return;
        }

        console.log("🔎 ARANAN SLUG:", slug);

        const response = await fetch("/api/products", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(
                `API hatası: ${response.status}`
            );
        }

        products = await response.json();

        console.log(
            "📦 API ÜRÜN SAYISI:",
            products.length
        );

        const product = products.find(
            (item) =>
                String(item.slug).trim() ===
                String(slug).trim()
        );

        if (!product) {
            console.error(
                "❌ ÜRÜN BULUNAMADI:",
                slug
            );

            showNotFound();
            return;
        }

        console.log(
            "✅ ÜRÜN BULUNDU:",
            product.name
        );

        updateSeo(product);
        injectStructuredData(product);

        document.getElementById(
            "detailCategory"
        ).textContent =
            `${product.brand} • ${product.category}`;

        document.getElementById(
            "detailTitle"
        ).textContent =
            `${product.name} İncelemesi`;

        document.getElementById(
            "detailDescription"
        ).textContent =
            product.description || "";

        document.getElementById(
            "detailRating"
        ).textContent =
            product.rating ?? "0";

        document.getElementById(
            "detailStars"
        ).textContent =
            createStars(product.rating);

        document.getElementById(
            "detailVerdict"
        ).textContent =
            product.verdict || "";

        document.getElementById(
            "detailPrice"
        ).textContent =
            product.price || "Fiyat bilgisi yok";

        fillList(
            "prosList",
            product.pros
        );

        fillList(
            "consList",
            product.cons
        );

        fillList(
            "shouldBuyList",
            product.shouldBuy
        );

        fillList(
            "shouldNotBuyList",
            product.shouldNotBuy
        );

        const specsTable =
            document.getElementById("specsTable");

        specsTable.innerHTML = "";

        const specs =
            product.specs &&
            typeof product.specs === "object"
                ? product.specs
                : {};

        Object.entries(specs).forEach(
            ([key, value]) => {
                const row =
                    document.createElement("tr");

                const keyCell =
                    document.createElement("th");

                const valueCell =
                    document.createElement("td");

                keyCell.textContent = key;
                valueCell.textContent = value;

                row.appendChild(keyCell);
                row.appendChild(valueCell);

                specsTable.appendChild(row);
            }
        );

        document.getElementById(
            "finalVerdict"
        ).textContent =
            product.finalVerdict ||
            `${product.name}, ${
                product.verdict || "genel olarak başarılı"
            } kategorisinde değerlendirilebilir. ` +
            `Burak Review puanı: ${product.rating}/5.`;

        const image =
            document.getElementById("detailImage");

        const fallback =
            document.getElementById("detailIcon");

        if (product.image) {
            image.src = product.image;

            image.alt =
                `${product.brand} ${product.name}`;

            image.style.display = "block";

            fallback.style.display = "none";

            image.onerror = () => {
                image.style.display = "none";
                fallback.textContent = "📦";
                fallback.style.display = "grid";
            };
        } else {
            image.style.display = "none";
            fallback.textContent = "📦";
            fallback.style.display = "grid";
        }

        notFound.style.display = "none";
        content.style.display = "grid";

    } catch (error) {
        console.error(
            "❌ ÜRÜN YÜKLEME HATASI:",
            error
        );

        showNotFound();
    }
}

loadProduct();
