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


        card.innerHTML = `

            <div class="product-image">

                <img
                    src="${product.image}"
                    alt="${product.brand} ${product.name}"
                    onerror="this.style.display='none'; this.parentElement.textContent='${product.category}'"
                >

            </div>


            <div class="product-info">

                <div class="product-category">
                    ${product.brand} • ${product.category}
                </div>


                <h3>
                    ${product.name}
                </h3>


                <div class="rating">

                    <span class="stars">
                        ${createStars(product.rating)}
                    </span>

                    <strong>
                        ${product.rating}
                    </strong>

                    <span>
                        / 5
                    </span>

                </div>


                <div class="verdict">

                    <span>●</span>

                    ${product.verdict}

                </div>


                <div class="product-bottom">

                    <strong class="price">
                        ${product.price}
                    </strong>


                    <button
                        class="review-btn"
                        type="button">

                        İncelemeyi Gör →

                    </button>

                </div>

            </div>
        `;


        card
            .querySelector(".review-btn")
            .addEventListener("click", () => {

                window.location.href =
                    `product.html?urun=${product.slug}`;

            });


        productsContainer.appendChild(card);

    });

}


async function loadProducts() {

    try {

        const response =
            await fetch("data/products.json");

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

        productsContainer.innerHTML = `
            <div class="empty-state">
                <h3>Ürünler yüklenemedi.</h3>
                <p>
                    Ürün kataloğunu kontrol edip sayfayı yenileyin.
                </p>
            </div>
        `;

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
