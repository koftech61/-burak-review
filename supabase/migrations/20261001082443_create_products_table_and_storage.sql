/*
# Create products table and product-images storage bucket

## 1. Purpose
Move the Burak Review product catalogue off the local SQLite database and
`products.json` file onto Supabase, so the catalogue has a single, durable
source of truth that survives server restarts and redeploys.

## 2. New Tables

### `products`
The public product catalogue. Column set mirrors the existing SQLite model
so the frontend JSON contract is unchanged.

- `id`             uuid, primary key (generated)
- `slug`           text, unique, not null  - URL identifier used by product.html
- `brand`          text, not null          - e.g. "Sony"
- `name`           text, not null          - product display name
- `category`       text, not null          - Kulaklık / Klavye / Mouse / Telefon / Laptop
- `image`          text, default ''        - image URL or storage path
- `rating`         numeric(2,1), 0..5      - Burak Review score
- `verdict`        text, default ''        - short verdict badge text
- `price`          text, default ''        - reviewed price (free text)
- `description`    text, default ''        - short summary
- `pros`           jsonb, default []       - list of strengths
- `cons`           jsonb, default []       - list of weaknesses
- `should_buy`     jsonb, default []       - target audience
- `should_not_buy` jsonb, default []       - who should avoid it
- `specs`          jsonb, default {}       - key/value technical specs
- `final_verdict`  text, default ''        - long closing assessment
- `created_at`     timestamptz, default now()

## 3. Indexes
- `products_slug_key` (unique) - fast lookup by slug on the detail page.
- `products_category_idx` - fast category filtering.
- `products_created_at_idx` - catalogue is listed newest-first.

## 4. Storage
- Creates a public bucket `product-images` for admin-uploaded product photos.
- Public read so product images render on the public site.

## 5. Security (RLS)
- Row Level Security is ENABLED on `products`.
- SELECT: open to `anon, authenticated` - the catalogue is intentionally public.
- INSERT / UPDATE / DELETE: open to `anon, authenticated` because the current
  admin write path is the Python server holding the anon key (the custom
  admin session/CSRF check lives in Python, not in Supabase Auth).
  NOTE: once the admin system is migrated to Supabase Auth (planned stage 2),
  these three policies must be tightened to `TO authenticated` with an
  ownership/role check.
- Storage: public read on `product-images`; write policies for the server-side
  upload path, same follow-up note applies.

## 6. Notes
- Uses `IF NOT EXISTS` / `DROP POLICY IF EXISTS` so the migration is safe to re-run.
- No data is dropped or altered.
*/

CREATE TABLE IF NOT EXISTS products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE,
    brand text NOT NULL,
    name text NOT NULL,
    category text NOT NULL,
    image text NOT NULL DEFAULT '',
    rating numeric(2,1) NOT NULL DEFAULT 0 CHECK (rating >= 0 AND rating <= 5),
    verdict text NOT NULL DEFAULT '',
    price text NOT NULL DEFAULT '',
    description text NOT NULL DEFAULT '',
    pros jsonb NOT NULL DEFAULT '[]'::jsonb,
    cons jsonb NOT NULL DEFAULT '[]'::jsonb,
    should_buy jsonb NOT NULL DEFAULT '[]'::jsonb,
    should_not_buy jsonb NOT NULL DEFAULT '[]'::jsonb,
    specs jsonb NOT NULL DEFAULT '{}'::jsonb,
    final_verdict text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS products_category_idx ON products (category);
CREATE INDEX IF NOT EXISTS products_created_at_idx ON products (created_at DESC);

ALTER TABLE products ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "public_select_products" ON products;
CREATE POLICY "public_select_products" ON products FOR SELECT
TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_insert_products" ON products;
CREATE POLICY "public_insert_products" ON products FOR INSERT
TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "public_update_products" ON products;
CREATE POLICY "public_update_products" ON products FOR UPDATE
TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "public_delete_products" ON products;
CREATE POLICY "public_delete_products" ON products FOR DELETE
TO anon, authenticated USING (true);

INSERT INTO storage.buckets (id, name, public)
VALUES ('product-images', 'product-images', true)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "product_images_public_read" ON storage.objects;
CREATE POLICY "product_images_public_read" ON storage.objects FOR SELECT
TO anon, authenticated USING (bucket_id = 'product-images');

DROP POLICY IF EXISTS "product_images_insert" ON storage.objects;
CREATE POLICY "product_images_insert" ON storage.objects FOR INSERT
TO anon, authenticated WITH CHECK (bucket_id = 'product-images');

DROP POLICY IF EXISTS "product_images_update" ON storage.objects;
CREATE POLICY "product_images_update" ON storage.objects FOR UPDATE
TO anon, authenticated USING (bucket_id = 'product-images')
WITH CHECK (bucket_id = 'product-images');

DROP POLICY IF EXISTS "product_images_delete" ON storage.objects;
CREATE POLICY "product_images_delete" ON storage.objects FOR DELETE
TO anon, authenticated USING (bucket_id = 'product-images');
