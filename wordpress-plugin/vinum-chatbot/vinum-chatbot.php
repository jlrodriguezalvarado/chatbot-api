<?php
/**
 * Plugin Name: Vinum Chatbot
 * Plugin URI: https://github.com/vinum/chatbot-api
 * Description: Floating chatbot widget with configurable API key, endpoint, title, color and image. Includes "Aggiorna conoscenza del chatbot" refresh action.
 * Version: 1.0.0
 * Author: Vinum
 * Requires at least: 5.9
 * Requires PHP: 7.4
 */

if (!defined('ABSPATH')) {
    exit;
}

define('VINUM_CHATBOT_OPTION', 'vinum_chatbot_settings');
define('VINUM_CHATBOT_VERSION', '1.0.0');

/**
 * Default settings.
 *
 * @return array<string, string>
 */
function vinum_chatbot_defaults() {
    return array(
        'api_key'            => '',
        'api_url'            => '',
        'title'              => 'Chat',
        'welcome_message'    => '',
        'input_placeholder'   => 'Escribe tu mensaje...',
        'conversation_ttl'   => '60',
        'button_color'       => '#6E56CF',
        'button_image_url'   => '',
        'loading_gif_url'    => '',
        'refresh_url'        => '',
    );
}

/**
 * Get plugin settings from database.
 *
 * @return array<string, string>
 */
function vinum_chatbot_get_settings() {
    $saved = get_option(VINUM_CHATBOT_OPTION, array());
    if (!is_array($saved)) {
        $saved = array();
    }
    return array_merge(vinum_chatbot_defaults(), $saved);
}

/**
 * Register settings and add admin menu.
 */
function vinum_chatbot_admin_init() {
    register_setting(
        'vinum_chatbot_options',
        VINUM_CHATBOT_OPTION,
        array(
            'type'              => 'array',
            'sanitize_callback' => 'vinum_chatbot_sanitize_settings',
        )
    );
}

/**
 * Sanitize settings before save.
 *
 * @param array<string, string> $input Raw input.
 * @return array<string, string>
 */
function vinum_chatbot_sanitize_settings($input) {
    if (!is_array($input)) {
        return vinum_chatbot_defaults();
    }
    $out = vinum_chatbot_defaults();
    if (isset($input['api_key'])) {
        $out['api_key'] = sanitize_text_field($input['api_key']);
    }
    if (isset($input['api_url'])) {
        $out['api_url'] = esc_url_raw(trim($input['api_url']));
    }
    if (isset($input['title'])) {
        $out['title'] = sanitize_text_field($input['title']);
    }
    if (isset($input['welcome_message'])) {
        $out['welcome_message'] = wp_kses_post($input['welcome_message']);
    }
    if (isset($input['input_placeholder'])) {
        $out['input_placeholder'] = sanitize_text_field($input['input_placeholder']);
    }
    if (isset($input['conversation_ttl'])) {
        $ttl = absint($input['conversation_ttl']);
        $out['conversation_ttl'] = (string) max(0, min(10080, $ttl)); // 0–10080 min (0–7 days)
    }
    if (isset($input['button_color'])) {
        $c = sanitize_hex_color($input['button_color']);
        $out['button_color'] = $c ? $c : $out['button_color'];
    }
    if (isset($input['button_image_url'])) {
        $out['button_image_url'] = esc_url_raw(trim($input['button_image_url']));
    }
    if (isset($input['loading_gif_url'])) {
        $url = esc_url_raw(trim($input['loading_gif_url']));
        $out['loading_gif_url'] = (preg_match('/\.gif(\?|$)/i', $url)) ? $url : '';
    }
    if (isset($input['refresh_url'])) {
        $out['refresh_url'] = esc_url_raw(trim($input['refresh_url']));
    }
    return $out;
}

/**
 * Add admin menu item.
 */
function vinum_chatbot_admin_menu() {
    add_options_page(
        __('Vinum Chatbot', 'vinum-chatbot'),
        __('Vinum Chatbot', 'vinum-chatbot'),
        'manage_options',
        'vinum-chatbot',
        'vinum_chatbot_options_page'
    );
}

/**
 * Enqueue admin scripts (for refresh button and color picker).
 */
function vinum_chatbot_admin_scripts($hook) {
    if ($hook !== 'settings_page_vinum-chatbot') {
        return;
    }
    wp_enqueue_media();
    wp_enqueue_style('wp-color-picker');
    wp_enqueue_script(
        'vinum-chatbot-admin',
        plugin_dir_url(__FILE__) . 'assets/vinum-chatbot-admin.js',
        array('jquery', 'wp-color-picker'),
        VINUM_CHATBOT_VERSION,
        true
    );
    wp_localize_script('vinum-chatbot-admin', 'vinumChatbotAdmin', array(
        'nonce'   => wp_create_nonce('vinum_chatbot_refresh'),
        'refreshUrl' => esc_url(vinum_chatbot_get_settings()['refresh_url']),
        'apiKey'  => vinum_chatbot_get_settings()['api_key'],
        'i18n'    => array(
            'refreshing' => __('Refrescando...', 'vinum-chatbot'),
            'done'       => __('Hecho', 'vinum-chatbot'),
            'error'      => __('Error al refrescar', 'vinum-chatbot'),
        ),
    ));
}

/**
 * Render options page.
 */
function vinum_chatbot_options_page() {
    if (!current_user_can('manage_options')) {
        return;
    }
    $settings = vinum_chatbot_get_settings();
    ?>
    <div class="wrap">
        <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
        <form action="options.php" method="post" id="vinum-chatbot-form">
            <?php settings_fields('vinum_chatbot_options'); ?>
            <table class="form-table" role="presentation">
                <tr>
                    <th scope="row"><label for="vinum_api_key"><?php esc_html_e('API Key', 'vinum-chatbot'); ?></label></th>
                    <td>
                        <input type="password" id="vinum_api_key" name="<?php echo esc_attr(VINUM_CHATBOT_OPTION); ?>[api_key]" value="<?php echo esc_attr($settings['api_key']); ?>" class="regular-text" autocomplete="off" />
                        <p class="description"><?php esc_html_e('API key for backend authentication.', 'vinum-chatbot'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="vinum_api_url"><?php esc_html_e('Endpoint URL', 'vinum-chatbot'); ?></label></th>
                    <td>
                        <input type="url" id="vinum_api_url" name="<?php echo esc_attr(VINUM_CHATBOT_OPTION); ?>[api_url]" value="<?php echo esc_attr($settings['api_url']); ?>" class="large-text" placeholder="https://api.example.com" />
                        <p class="description"><?php esc_html_e('Base URL of the chatbot backend (e.g. https://api.example.com).', 'vinum-chatbot'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="vinum_title"><?php esc_html_e('Title', 'vinum-chatbot'); ?></label></th>
                    <td>
                        <input type="text" id="vinum_title" name="<?php echo esc_attr(VINUM_CHATBOT_OPTION); ?>[title]" value="<?php echo esc_attr($settings['title']); ?>" class="regular-text" />
                        <p class="description"><?php esc_html_e('Chat window and button title.', 'vinum-chatbot'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="vinum_welcome_message"><?php esc_html_e('Welcome message', 'vinum-chatbot'); ?></label></th>
                    <td>
                        <textarea id="vinum_welcome_message" name="<?php echo esc_attr(VINUM_CHATBOT_OPTION); ?>[welcome_message]" rows="3" class="large-text"><?php echo esc_textarea($settings['welcome_message']); ?></textarea>
                        <p class="description"><?php esc_html_e('Message shown when the user opens the chat. Leave empty for none.', 'vinum-chatbot'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="vinum_input_placeholder"><?php esc_html_e('Input placeholder', 'vinum-chatbot'); ?></label></th>
                    <td>
                        <input type="text" id="vinum_input_placeholder" name="<?php echo esc_attr(VINUM_CHATBOT_OPTION); ?>[input_placeholder]" value="<?php echo esc_attr($settings['input_placeholder']); ?>" class="regular-text" />
                        <p class="description"><?php esc_html_e('Placeholder text for the chat input box.', 'vinum-chatbot'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="vinum_conversation_ttl"><?php esc_html_e('Conversation retention (minutes)', 'vinum-chatbot'); ?></label></th>
                    <td>
                        <input type="number" id="vinum_conversation_ttl" name="<?php echo esc_attr(VINUM_CHATBOT_OPTION); ?>[conversation_ttl]" value="<?php echo esc_attr($settings['conversation_ttl']); ?>" min="0" max="10080" class="small-text" />
                        <p class="description"><?php esc_html_e('How long to keep the conversation in the browser (localStorage). 0 = no persistence. Max 10080 (7 days).', 'vinum-chatbot'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="vinum_button_color"><?php esc_html_e('Button color', 'vinum-chatbot'); ?></label></th>
                    <td>
                        <input type="text" id="vinum_button_color" name="<?php echo esc_attr(VINUM_CHATBOT_OPTION); ?>[button_color]" value="<?php echo esc_attr($settings['button_color']); ?>" class="vinum-color-picker" />
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="vinum_button_image_url"><?php esc_html_e('Button image', 'vinum-chatbot'); ?></label></th>
                    <td>
                        <input type="hidden" id="vinum_button_image_url" name="<?php echo esc_attr(VINUM_CHATBOT_OPTION); ?>[button_image_url]" value="<?php echo esc_attr($settings['button_image_url']); ?>" />
                        <button type="button" id="vinum-select-button-image" class="button"><?php esc_html_e('Select from Media Library', 'vinum-chatbot'); ?></button>
                        <button type="button" id="vinum-remove-button-image" class="button"><?php esc_html_e('Remove', 'vinum-chatbot'); ?></button>
                        <span id="vinum-button-image-preview" style="margin-left:10px;"></span>
                        <p class="description"><?php esc_html_e('Image for the floating button. Leave empty for default icon.', 'vinum-chatbot'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="vinum_loading_gif_url"><?php esc_html_e('Loading GIF', 'vinum-chatbot'); ?></label></th>
                    <td>
                        <input type="hidden" id="vinum_loading_gif_url" name="<?php echo esc_attr(VINUM_CHATBOT_OPTION); ?>[loading_gif_url]" value="<?php echo esc_attr($settings['loading_gif_url']); ?>" />
                        <button type="button" id="vinum-select-loading-gif" class="button"><?php esc_html_e('Select GIF from Media Library', 'vinum-chatbot'); ?></button>
                        <button type="button" id="vinum-remove-loading-gif" class="button"><?php esc_html_e('Remove', 'vinum-chatbot'); ?></button>
                        <span id="vinum-loading-gif-preview" style="margin-left:10px;"></span>
                        <p class="description"><?php esc_html_e('GIF shown while waiting for a response. Only GIF format is accepted. Leave empty for 3 bouncing dots.', 'vinum-chatbot'); ?></p>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="vinum_refresh_url"><?php esc_html_e('Refresh knowledge URL', 'vinum-chatbot'); ?></label></th>
                    <td>
                        <input type="url" id="vinum_refresh_url" name="<?php echo esc_attr(VINUM_CHATBOT_OPTION); ?>[refresh_url]" value="<?php echo esc_attr($settings['refresh_url']); ?>" class="large-text" placeholder="https://..." />
                        <p class="description"><?php esc_html_e('URL called when "Aggiorna conoscenza del chatbot" is clicked. Backend should trigger knowledge refresh.', 'vinum-chatbot'); ?></p>
                    </td>
                </tr>
            </table>
            <p class="submit">
                <?php submit_button(__('Save settings', 'vinum-chatbot'), 'primary', 'submit', false); ?>
            </p>
        </form>

        <hr />
        <h2><?php esc_html_e('Knowledge refresh', 'vinum-chatbot'); ?></h2>
        <p>
            <button type="button" id="vinum-refresh-knowledge" class="button button-secondary">
                <?php esc_html_e('Aggiorna conoscenza del chatbot', 'vinum-chatbot'); ?>
            </button>
            <span id="vinum-refresh-status" style="margin-left:8px;"></span>
        </p>
        <p class="description"><?php esc_html_e('Uses the "Refresh knowledge URL" above. Save settings first if you changed it.', 'vinum-chatbot'); ?></p>
    </div>
    <?php
}

/**
 * Enqueue frontend widget only when we have api_url (and optionally show only when api_key is set).
 */
function vinum_chatbot_enqueue_widget() {
    $settings = vinum_chatbot_get_settings();
    $api_url = isset($settings['api_url']) ? trim($settings['api_url']) : '';
    if ($api_url === '') {
        return;
    }
    wp_enqueue_script(
        'vinum-chatbot-widget',
        plugin_dir_url(__FILE__) . 'assets/vinum-chatbot-widget.js',
        array(),
        VINUM_CHATBOT_VERSION,
        true
    );
    wp_add_inline_script('vinum-chatbot-widget', 'window.vinumChatbotConfig=' . wp_json_encode(array(
        'apiKey'            => isset($settings['api_key']) ? $settings['api_key'] : '',
        'apiUrl'            => $api_url,
        'title'             => isset($settings['title']) ? $settings['title'] : 'Chat',
        'welcomeMessage'    => isset($settings['welcome_message']) ? $settings['welcome_message'] : '',
        'inputPlaceholder'  => isset($settings['input_placeholder']) ? $settings['input_placeholder'] : 'Escribe tu mensaje...',
        'conversationTtl'   => isset($settings['conversation_ttl']) ? (int) $settings['conversation_ttl'] : 60,
        'buttonColor'       => isset($settings['button_color']) ? $settings['button_color'] : '#6E56CF',
        'buttonImageUrl'    => isset($settings['button_image_url']) ? trim($settings['button_image_url']) : '',
        'loadingGifUrl'     => isset($settings['loading_gif_url']) ? trim($settings['loading_gif_url']) : '',
    )) . ';', 'before');
}

add_action('admin_init', 'vinum_chatbot_admin_init');
add_action('admin_menu', 'vinum_chatbot_admin_menu');
add_action('admin_enqueue_scripts', 'vinum_chatbot_admin_scripts');
add_action('wp_enqueue_scripts', 'vinum_chatbot_enqueue_widget');
