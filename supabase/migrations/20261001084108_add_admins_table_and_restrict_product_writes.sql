/*
# Add admins table and restrict product writes to admins

## 1. Purpose
Move product write access off the anonymous key and onto authenticated admin
users managed by Supabase Auth. Public visitors keep read-only access.

## 2. New Tables

### `admins`
Allow-list of users who may manage the catalogue.
- `user_id`    uuid, primary key, references auth.users(id) ON DELETE CASCADE
- `created_at` timestamptz, default now()

## 3. Security

### `admins`
- RLS ENABLED.
- SELECT: a signed-in user may read only their own row (used by the admin page
  to confirm admin status).
- NO insert/update/delete policies for `anon` or `authenticated`, so no client
  can add themselves as an admin. Rows are added deliberately via SQL / service role.

### `products`
- SELECT: unchanged, public (anon + authenticated) - the catalogue is public.
- INSERT / UPDATE / DELETE: now restricted to authenticated users whose id is
  present in `admins`. Anonymous visitors can no longer write.

### `storage.objects` (bucket `product-images`)
- SELECT: unchanged, public read.
- INSERT / UPDATE / DELETE: now restricted to authenticated admins.

## 4. Notes
- Safe to re-run (DROP POLICY IF EXISTS before each CREATE).
- No columns, tables or rows are dropped; existing products are untouched.
- Follow-up: after adding your first admin, replace the email below and run:
    INSERT INTO admins (user_id)
    SELECT id FROM auth.users WHERE email = 'ADMIN_EMAIL'
    ON CONFLICT (user_id) DO NOTHING;
*/

CREATE TABLE IF NOT EXISTS admins (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE admins ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "admins_read_self" ON admins;
CREATE POLICY "admins_read_self" ON admins FOR SELECT
TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "public_select_products" ON products;
CREATE POLICY "public_select_products" ON products FOR SELECT
TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "public_insert_products" ON products;
DROP POLICY IF EXISTS "admin_insert_products" ON products;
CREATE POLICY "admin_insert_products" ON products FOR INSERT
TO authenticated
WITH CHECK (EXISTS (SELECT 1 FROM admins WHERE admins.user_id = auth.uid()));

DROP POLICY IF EXISTS "public_update_products" ON products;
DROP POLICY IF EXISTS "admin_update_products" ON products;
CREATE POLICY "admin_update_products" ON products FOR UPDATE
TO authenticated
USING (EXISTS (SELECT 1 FROM admins WHERE admins.user_id = auth.uid()))
WITH CHECK (EXISTS (SELECT 1 FROM admins WHERE admins.user_id = auth.uid()));

DROP POLICY IF EXISTS "public_delete_products" ON products;
DROP POLICY IF EXISTS "admin_delete_products" ON products;
CREATE POLICY "admin_delete_products" ON products FOR DELETE
TO authenticated
USING (EXISTS (SELECT 1 FROM admins WHERE admins.user_id = auth.uid()));

DROP POLICY IF EXISTS "product_images_public_read" ON storage.objects;
CREATE POLICY "product_images_public_read" ON storage.objects FOR SELECT
TO anon, authenticated USING (bucket_id = 'product-images');

DROP POLICY IF EXISTS "product_images_insert" ON storage.objects;
DROP POLICY IF EXISTS "admin_insert_product_images" ON storage.objects;
CREATE POLICY "admin_insert_product_images" ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'product-images'
    AND EXISTS (SELECT 1 FROM admins WHERE admins.user_id = auth.uid())
);

DROP POLICY IF EXISTS "product_images_update" ON storage.objects;
DROP POLICY IF EXISTS "admin_update_product_images" ON storage.objects;
CREATE POLICY "admin_update_product_images" ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id = 'product-images'
    AND EXISTS (SELECT 1 FROM admins WHERE admins.user_id = auth.uid())
)
WITH CHECK (
    bucket_id = 'product-images'
    AND EXISTS (SELECT 1 FROM admins WHERE admins.user_id = auth.uid())
);

DROP POLICY IF EXISTS "product_images_delete" ON storage.objects;
DROP POLICY IF EXISTS "admin_delete_product_images" ON storage.objects;
CREATE POLICY "admin_delete_product_images" ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id = 'product-images'
    AND EXISTS (SELECT 1 FROM admins WHERE admins.user_id = auth.uid())
);
