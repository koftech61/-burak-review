let products = [];

const params = new URLSearchParams(window.location.search);
const slug = params.get("urun");

const notFound = document.getElementById("productNotFound");
const content = document.getElementById("productContent");


async function loadProduct() {

    try {

        const response =
            await fetch("data/products.json");

        if (!response.ok) {
            throw new Error(
                `Ürün kataloğu yüklenemedi: ${response.status}`
            );
        }


        products = await response.json();


        if (!Array.isArray(products)) {
            throw new Error(
                "products.json geçerli bir ürün dizisi değil."
            );
        }


        const product =
            products.find(item => item.slug === slug);


        if (!product) {

            content.style.display = "none";
            notFound.style.display = "block";

            return;
        }


        document.title =
            `${product.name} İncelemesi | Burak Review`;


        const metaDescription =
            document.querySelector(
                'meta[name="description"]'
            );


        if (metaDescription) {

            metaDescription.setAttribute(
                "content",
                `${product.name} teknik özellikleri, artıları, eksileri ve Burak Review değerlendirmesi.`
            );

        }


        document.getElementById(
            "detailCategory"
        ).textContent =
            `${product.brand} • ${product.category}`;


        document.getElementById(
            "detailTitle"
        ).textContent =
            `${product.icon} ${product.name} İncelemesi`;


        document.getElementById(
            "detailDescription"
        ).textContent =
            product.description;


        document.getElementById(
            "detailRating"
        ).textContent =
            product.rating;


        const roundedRating =
            Math.round(product.rating);


        document.getElementById(
            "detailStars"
        ).textContent =
            "★".repeat(roundedRating) +
            "☆".repeat(5 - roundedRating);


        document.getElementById(
            "detailVerdict"
        ).textContent =
            product.verdict;


        document.getElementById(
            "detailPrice"
        ).textContent =
            product.price;


        const image =
            document.getElementById("detailImage");


        const fallback =
            document.getElementById("detailIcon");


        image.alt =
            `${product.brand} ${product.name}`;


        image.src =
            product.image;


        fallback.textContent =
            product.icon;


        image.addEventListener(
            "error",
            () => {

                image.style.display = "none";
                fallback.style.display = "grid";

            }
        );


        function fillList(id, items) {

            const list =
                document.getElementById(id);

            list.innerHTML = "";


            items.forEach(item => {

                const li =
                    document.createElement("li");

                li.textContent = item;

                list.appendChild(li);

            });

        }


        fillList(
            "prosList",
            product.pros || []
        );


        fillList(
            "consList",
            product.cons || []
        );


        fillList(
            "shouldBuyList",
            product.shouldBuy || []
        );


        fillList(
            "shouldNotBuyList",
            product.shouldNotBuy || []
        );


        const specsTable =
            document.getElementById("specsTable");


        specsTable.innerHTML = "";


        Object.entries(
            product.specs || {}
        ).forEach(
            ([key, value]) => {

                const row =
                    document.createElement("tr");


                const keyCell =
                    document.createElement("th");


                const valueCell =
                    document.createElement("td");


                keyCell.textContent =
                    key;


                valueCell.textContent =
                    value;


                row.appendChild(keyCell);
                row.appendChild(valueCell);


                specsTable.appendChild(row);

            }
        );


        document.getElementById(
            "finalVerdict"
        ).textContent =
            `${product.name}, ${product.verdict.toLowerCase()} kategorisinde değerlendirilebilir. ` +
            `Burak Review puanı: ${product.rating}/5.`;


        notFound.style.display = "none";
        content.style.display = "block";


    } catch (error) {

        console.error(error);

        content.style.display = "none";
        notFound.style.display = "block";

    }

}


loadProduct();
