let products = [];

const productsContainer =
    document.getElementById("products");

const searchInput =
    document.getElementById("searchInput");

const productCount =
    document.getElementById("productCount");

let selectedCategory = "Tümü";


function createStars(rating) {

    const fullStars = Math.round(rating);

    return "★".repeat(fullStars) +
           "☆".repeat(5 - fullStars);
}


function renderProducts() {

    const search =
        searchInput.value
            .toLowerCase()
            .trim();


    const filtered =
        products.filter(product => {

            const categoryMatch =
                selectedCategory === "Tümü" ||
                product.category === selectedCategory;


            const searchMatch =
                product.name
                    .toLowerCase()
                    .includes(search) ||

                product.brand
                    .toLowerCase()
                    .includes(search) ||

                product.category
                    .toLowerCase()
                    .includes(search);


            return categoryMatch && searchMatch;
        });


    productsContainer.innerHTML = "";

    productCount.textContent =
        `${filtered.length} ürün`;


    filtered.forEach(product => {

        const card =
            document.createElement("article");

        card.className = "product";


        const imageDiv =
            document.createElement("div");
        imageDiv.className = "product-image";

        const img = document.createElement("img");

        if (product.image) {
            img.src = product.image;
        }

        img.alt =
            `${product.brand} ${product.name}`;

        img.addEventListener("error", () => {
            img.style.display = "none";
            imageDiv.textContent = product.category;
        });

        imageDiv.appendChild(img);
        card.appendChild(imageDiv);


        const infoDiv =
            document.createElement("div");
        infoDiv.className = "product-info";


        const categoryDiv =
            document.createElement("div");
        categoryDiv.className = "product-category";
        categoryDiv.textContent =
            `${product.brand} • ${product.category}`;

        infoDiv.appendChild(categoryDiv);


        const nameHeading =
            document.createElement("h3");
        nameHeading.textContent = product.name;

        infoDiv.appendChild(nameHeading);


        const ratingDiv =
            document.createElement("div");
        ratingDiv.className = "rating";

        const starsSpan =
            document.createElement("span");
        starsSpan.className = "stars";
        starsSpan.textContent =
            createStars(product.rating);

        ratingDiv.appendChild(starsSpan);

        const ratingStrong =
            document.createElement("strong");
        ratingStrong.textContent = product.rating;

        ratingDiv.appendChild(ratingStrong);

        const ratingSlash =
            document.createElement("span");
        ratingSlash.textContent = " / 5";

        ratingDiv.appendChild(ratingSlash);

        infoDiv.appendChild(ratingDiv);


        const verdictDiv =
            document.createElement("div");
        verdictDiv.className = "verdict";

        const verdictDot =
            document.createElement("span");
        verdictDot.textContent = "●";

        verdictDiv.appendChild(verdictDot);

        verdictDiv.appendChild(
            document.createTextNode(
                product.verdict || ""
            )
        );

        infoDiv.appendChild(verdictDiv);


        const bottomDiv =
            document.createElement("div");
        bottomDiv.className = "product-bottom";

        const priceStrong =
            document.createElement("strong");
        priceStrong.className = "price";
        priceStrong.textContent = product.price || "";

        bottomDiv.appendChild(priceStrong);

        const reviewBtn =
            document.createElement("button");
        reviewBtn.className = "review-btn";
        reviewBtn.type = "button";
        reviewBtn.textContent = "İncelemeyi Gör →";

        reviewBtn.addEventListener("click", () => {
            window.location.href =
                `product.html?urun=${encodeURIComponent(product.slug)}`;
        });

        bottomDiv.appendChild(reviewBtn);

        infoDiv.appendChild(bottomDiv);


        card.appendChild(infoDiv);


        productsContainer.appendChild(card);

    });

}


async function loadProducts() {

    try {

        const response =
            await fetch("/api/products");

        if (!response.ok) {
            throw new Error(
                `Ürün kataloğu yüklenemedi: ${response.status}`
            );
        }


        products =
            await response.json();


        if (!Array.isArray(products)) {
            throw new Error(
                "products.json bir ürün dizisi içermiyor."
            );
        }


        renderProducts();


    } catch (error) {

        console.error(error);

        productsContainer.innerHTML = "";

        const emptyState =
            document.createElement("div");
        emptyState.className = "empty-state";

        const emptyHeading =
            document.createElement("h3");
        emptyHeading.textContent =
            "Ürünler yüklenemedi.";

        emptyState.appendChild(emptyHeading);

        const emptyPara =
            document.createElement("p");
        emptyPara.textContent =
            "Ürün kataloğunu kontrol edip sayfayı yenileyin.";

        emptyState.appendChild(emptyPara);

        productsContainer.appendChild(emptyState);

        productCount.textContent =
            "0 ürün";

    }

}


searchInput.addEventListener(
    "input",
    renderProducts
);


document
    .querySelectorAll(".categories button")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                document
                    .querySelectorAll(".categories button")
                    .forEach(item => {

                        item.classList.remove("active");

                    });


                button.classList.add("active");


                selectedCategory =
                    button.dataset.category;


                renderProducts();

            }
        );

    });


document
    .querySelector(
        '.categories button[data-category="Tümü"]'
    )
    .classList.add("active");


loadProducts();
