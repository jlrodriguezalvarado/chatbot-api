<?php
/**
 * Plugin Name: Vinum Wines
 * Plugin URI: https://github.com/vinum/chatbot-api
 * Description: Registers wine products from xtrawine schema (REST API) and stores full wine data as WooCommerce products with custom meta.
 * Version: 1.0.0
 * Author: Vinum
 * Requires at least: 5.9
 * Requires PHP: 7.4
 * WC requires at least: 5.0
 * WC tested up to: 10.5
 */

if (!defined('ABSPATH')) {
    exit;
}

define('VINUM_WINES_META_KEY', '_vinum_wine_data');

/**
 * Declare compatibility with WooCommerce features (e.g. HPOS) to avoid "incompatible plugins" warnings.
 * This plugin only creates products and stores meta; it does not use orders.
 */
add_action('before_woocommerce_init', function () {
    if (class_exists(\Automattic\WooCommerce\Utilities\FeaturesUtil::class)) {
        \Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility('custom_order_tables', __FILE__, true);
    }
});

/**
 * Check if WooCommerce is active.
 */
function vinum_wines_woocommerce_active() {
    return class_exists('WooCommerce');
}

/**
 * Build product description from wine data for WooCommerce.
 *
 * @param array $wine Full wine object (xtrawine schema).
 * @return string
 */
function vinum_wines_build_description($wine) {
    $parts = array();
    $p = isset($wine['product']) ? $wine['product'] : array();
    $tasting = isset($wine['tasting_notes']) ? $wine['tasting_notes'] : array();
    $pairings = isset($wine['pairings']) ? $wine['pairings'] : array();
    $tech = isset($wine['technical_sheet']) ? $wine['technical_sheet'] : array();

    if (!empty($p['type'])) {
        $parts[] = 'Type: ' . $p['type'];
    }
    if (!empty($p['country'])) {
        $parts[] = 'Country: ' . $p['country'];
    }
    if (!empty($p['region'])) {
        $parts[] = 'Region: ' . $p['region'];
    }
    if (isset($p['vintage_year']) && $p['vintage_year']) {
        $parts[] = 'Vintage: ' . $p['vintage_year'];
    }
    if (!empty($p['denomination'])) {
        $parts[] = 'Denomination: ' . $p['denomination'];
    }
    if (!empty($p['producer'])) {
        $parts[] = 'Producer: ' . $p['producer'];
    }
    if (!empty($p['grape_varieties']) && is_array($p['grape_varieties'])) {
        $grapes = array_map(function ($g) {
            return $g['name'] . (isset($g['percentage']) ? ' ' . $g['percentage'] . '%' : '');
        }, $p['grape_varieties']);
        $parts[] = 'Grape varieties: ' . implode(', ', $grapes);
    }

    if (!empty($tasting['color'])) {
        $parts[] = "\nColor: " . $tasting['color'];
    }
    if (!empty($tasting['perfume'])) {
        $parts[] = "Perfume: " . $tasting['perfume'];
    }
    if (!empty($tasting['taste'])) {
        $parts[] = "Taste: " . $tasting['taste'];
    }
    if (!empty($pairings['description'])) {
        $parts[] = "\nPairings: " . $pairings['description'];
    }
    if (!empty($tech['wine_making'])) {
        $parts[] = "\nWine making: " . $tech['wine_making'];
    }
    if (!empty($tech['aging'])) {
        $parts[] = "Aging: " . $tech['aging'];
    }

    return implode("\n\n", $parts);
}

/**
 * Build searchable text content (for Vector Store / chatbot). Same as description but can be extended.
 */
function vinum_wines_build_content($wine) {
    return vinum_wines_build_description($wine);
}

/**
 * REST: Create a single wine product.
 */
function vinum_rest_create_product(\WP_REST_Request $request) {
    if (!vinum_wines_woocommerce_active()) {
        return new \WP_REST_Response(array('error' => 'WooCommerce is not active.'), 503);
    }

    $body = $request->get_json_params();
    if (empty($body) || empty($body['product']['name'])) {
        return new \WP_REST_Response(array('error' => 'Invalid wine payload: product.name required.'), 400);
    }

    $name = sanitize_text_field($body['product']['name']);
    $price = 0;
    if (!empty($body['pricing']['price'])) {
        $price = floatval($body['pricing']['price']);
    }
    $description = vinum_wines_build_description($body);
    $short_desc = '';
    if (!empty($body['tasting_notes']['taste'])) {
        $short_desc = wp_kses_post($body['tasting_notes']['taste']);
    } elseif (!empty($body['tasting_notes']['perfume'])) {
        $short_desc = wp_kses_post($body['tasting_notes']['perfume']);
    }
    if (strlen($short_desc) > 300) {
        $short_desc = wp_trim_words($short_desc, 30);
    }

    $product = new \WC_Product_Simple();
    $product->set_name($name);
    $product->set_status('publish');
    $product->set_description($description);
    $product->set_short_description($short_desc);
    $product->set_regular_price($price > 0 ? (string) $price : '');
    $product->set_sold_individually(false);

    $product_id = $product->save();
    if (!$product_id) {
        return new \WP_REST_Response(array('error' => 'Failed to create product.'), 500);
    }

    update_post_meta($product_id, VINUM_WINES_META_KEY, wp_json_encode($body));

    $main_image = null;
    if (!empty($body['media']['main_image'])) {
        $main_image = $body['media']['main_image'];
    } elseif (!empty($body['media']['images'][0])) {
        $main_image = $body['media']['images'][0];
    }
    if ($main_image) {
        $attach_id = vinum_wines_upload_image_from_url($main_image, $product_id);
        if ($attach_id) {
            $product->set_image_id($attach_id);
            $product->save();
        }
    }

    return new \WP_REST_Response(array(
        'id' => $product_id,
        'name' => $name,
        'message' => 'Product created.',
    ), 201);
}

/**
 * Upload image from URL and attach to product.
 *
 * @param string $url Image URL.
 * @param int $product_id Post ID (product).
 * @return int|false Attachment ID or false.
 */
function vinum_wines_upload_image_from_url($url, $product_id) {
    require_once ABSPATH . 'wp-admin/includes/file.php';
    require_once ABSPATH . 'wp-admin/includes/media.php';
    require_once ABSPATH . 'wp-admin/includes/image.php';

    $tmp = download_url($url);
    if (is_wp_error($tmp)) {
        return false;
    }
    $file_array = array(
        'name' => basename(parse_url($url, PHP_URL_PATH)) ?: 'wine.jpg',
        'tmp_name' => $tmp,
    );
    $attach_id = media_handle_sideload($file_array, $product_id);
    if (is_wp_error($attach_id)) {
        @unlink($tmp);
        return false;
    }
    return $attach_id;
}

/**
 * REST: List all wine products with full wine data.
 */
function vinum_rest_list_products(\WP_REST_Request $request) {
    if (!vinum_wines_woocommerce_active()) {
        return new \WP_REST_Response(array('error' => 'WooCommerce is not active.'), 503);
    }

    $per_page = (int) $request->get_param('per_page');
    if ($per_page <= 0 || $per_page > 100) {
        $per_page = 100;
    }
    $page = max(1, (int) $request->get_param('page'));

    $args = array(
        'post_type' => 'product',
        'post_status' => 'publish',
        'posts_per_page' => $per_page,
        'paged' => $page,
        'meta_query' => array(
            array(
                'key' => VINUM_WINES_META_KEY,
                'compare' => 'EXISTS',
            ),
        ),
    );
    $query = new \WP_Query($args);
    $products = array();
    foreach ($query->posts as $post) {
        $data = get_post_meta($post->ID, VINUM_WINES_META_KEY, true);
        $wine_data = is_string($data) ? json_decode($data, true) : $data;
        if (!is_array($wine_data)) {
            $wine_data = array();
        }
        $content = vinum_wines_build_content($wine_data);
        $product_url = get_permalink($post->ID);
        $products[] = array(
            'id' => $post->ID,
            'title' => $post->post_title,
            'content' => $content,
            'product_url' => $product_url ? $product_url : '',
            'wine_data' => $wine_data,
        );
    }

    $total = $query->found_posts;
    return new \WP_REST_Response(array(
        'products' => $products,
        'total' => (int) $total,
        'page' => $page,
        'per_page' => $per_page,
    ), 200);
}

/**
 * Permission: allow only authenticated users with manage_woocommerce or manage_options.
 */
function vinum_rest_permission(\WP_REST_Request $request) {
    return current_user_can('manage_woocommerce') || current_user_can('manage_options');
}

/**
 * Register REST routes.
 */
function vinum_wines_register_rest_routes() {
    register_rest_route('vinum/v1', '/products', array(
        array(
            'methods' => \WP_REST_Server::CREATABLE,
            'callback' => 'vinum_rest_create_product',
            'permission_callback' => 'vinum_rest_permission',
            'args' => array(),
        ),
        array(
            'methods' => \WP_REST_Server::READABLE,
            'callback' => 'vinum_rest_list_products',
            'permission_callback' => '__return_true',
            'args' => array(
                'per_page' => array(
                    'default' => 100,
                    'type' => 'integer',
                    'minimum' => 1,
                    'maximum' => 100,
                ),
                'page' => array(
                    'default' => 1,
                    'type' => 'integer',
                    'minimum' => 1,
                ),
            ),
        ),
    ));
}

add_action('rest_api_init', 'vinum_wines_register_rest_routes');
