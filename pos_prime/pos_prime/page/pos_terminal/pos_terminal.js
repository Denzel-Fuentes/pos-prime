// Kept so on_page_show can re-apply the page-head hiding without reaching
// across the whole Desk (other pages have a .page-head they still need).
var posWrapper = null;

frappe.pages['pos-terminal'].on_page_load = function(wrapper) {
	posWrapper = wrapper;

	frappe.ui.make_app_page({
		parent: wrapper,
		// No title: the page-head is hidden below, but on some Desk versions
		// the title still leaks into the navbar/breadcrumb area next to the
		// POS profile indicator ("POS Terminal <profile>").
		title: '',
		single_column: true,
	});

	// Breadcrumbs: POS Prime > POS Terminal
	frappe.breadcrumbs.add('POS Prime', 'pos-terminal');

	// Hide the page-head bar (title/indicator/breadcrumbs) entirely — the
	// Vue app is a full-screen kiosk UI and doesn't need it. The persistent
	// Desk navbar above it is left untouched.
	hidePageHead(wrapper);

	// Match navbar width: remove .container max-width, use navbar's 1rem padding
	var fullWidth = 'max-width:100%!important;width:100%!important;margin:0!important;padding-left:1rem!important;padding-right:1rem!important;';
	var noPad = 'padding:0!important;margin:0!important;max-width:100%!important;width:100%!important;';
	$(wrapper).find('.page-body').each(function() { this.style.cssText += fullWidth; });
	$(wrapper).find('.page-wrapper').each(function() { this.style.cssText += noPad; });
	$(wrapper).find('.layout-main').each(function() { this.style.cssText += noPad; });
	$(wrapper).find('.layout-main-section-wrapper').each(function() { this.style.cssText += noPad; });
	$(wrapper).find('.layout-main-section').each(function() { this.style.cssText += noPad; });

	// Create mount point
	$(wrapper).find('.layout-main-section').html('<div id="pos-prime-app"></div>');

	// Hide Frappe desk sidebar permanently on this page
	// v14/v15: aside.desk-sidebar   v16: .body-sidebar-container
	$('aside.desk-sidebar, .desk-sidebar, .body-sidebar-container').hide();

	// Size it to fill remaining viewport
	setTimeout(sizePosApp, 0);
	window.addEventListener('resize', sizePosApp);
	// Adapt when Frappe desk sidebar is toggled
	$(document.body).on('toggleSidebar', function() {
		setTimeout(sizePosApp, 300);
	});

	window.csrf_token = frappe.csrf_token;
	load_pos_prime_assets();
};

frappe.pages['pos-terminal'].on_page_show = function() {
	// Re-hide sidebar when returning to this page
	$('aside.desk-sidebar, .desk-sidebar, .body-sidebar-container').hide();
	hidePageHead(posWrapper);
	sizePosApp();
	window.addEventListener('resize', sizePosApp);
};

frappe.pages['pos-terminal'].on_page_hide = function() {
	window.removeEventListener('resize', sizePosApp);
	// Restore sidebar when navigating away
	$('aside.desk-sidebar, .desk-sidebar, .body-sidebar-container').show();
};

// Hides the page title / indicator bar of this page only. A plain .hide()
// isn't enough: Desk re-shows .page-head on its own (route changes, the
// sticky-header observer), which left an empty ~55px strip where the title
// used to be. A stylesheet rule scoped to this page's container wins over
// whatever inline display Desk sets, and never touches other pages.
function hidePageHead(wrapper) {
	var id = (wrapper && wrapper.id) || 'page-pos-terminal';
	if (!document.getElementById('pos-prime-page-head-style')) {
		$('<style id="pos-prime-page-head-style"></style>')
			.text(
				'#' + id + ' .page-head{display:none!important;}' +
				'#' + id + ' .page-body{padding-top:0!important;margin-top:0!important;}'
			)
			.appendTo(document.head);
	}
	if (wrapper) {
		$(wrapper).find('.page-head').hide();
	}
}

function sizePosApp() {
	var el = document.getElementById('pos-prime-app');
	if (!el) return;
	var top = el.getBoundingClientRect().top;
	el.style.height = 'calc(100vh - ' + Math.round(top) + 'px)';
	el.style.overflow = 'hidden';
}

async function load_pos_prime_assets() {
	try {
		// cache: 'no-store' — this URL has no content hash (unlike the JS/CSS
		// chunks it points to), so the browser's default HTTP cache would
		// otherwise keep resolving to whatever build was live the first time
		// this fetch ran, silently serving stale code after every later
		// `yarn build` until that cache entry expired or was manually cleared.
		var manifestRes = await fetch('/assets/pos_prime/frontend/.vite/manifest.json', { cache: 'no-store' });
		if (!manifestRes.ok) {
			throw new Error('Manifest not found (HTTP ' + manifestRes.status + ')');
		}
		var manifest = await manifestRes.json();

		var entry = manifest['index.html'] || manifest['src/main.ts'];
		if (!entry) {
			throw new Error('Entry point not found in manifest');
		}

		var cssFiles = new Set();
		function collectCSS(chunk) {
			if (chunk.css) {
				chunk.css.forEach(function(f) { cssFiles.add(f); });
			}
			if (chunk.imports) {
				chunk.imports.forEach(function(key) {
					if (manifest[key]) collectCSS(manifest[key]);
				});
			}
		}
		collectCSS(entry);

		cssFiles.forEach(function(cssFile) {
			if (!document.querySelector('link[href$="' + cssFile + '"]')) {
				var link = document.createElement('link');
				link.rel = 'stylesheet';
				link.href = '/assets/pos_prime/frontend/' + cssFile;
				document.head.appendChild(link);
			}
		});

		await import('/assets/pos_prime/frontend/' + entry.file);

		// Re-size after Vue app mounts
		setTimeout(sizePosApp, 100);
	} catch (e) {
		console.error('Failed to load POS Prime:', e);
		var el = document.getElementById('pos-prime-app');
		if (el) {
			el.innerHTML =
				'<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#666;">' +
				'<div style="text-align:center;">' +
				'<p style="font-size:16px;font-weight:600;">Failed to load POS Prime</p>' +
				'<p style="font-size:13px;margin-top:8px;color:#999;">' + e.message + '</p>' +
				'<p style="font-size:13px;margin-top:8px;"><a href="#" onclick="location.reload();return false;" style="color:#2490ef;">Try refreshing</a></p>' +
				'</div></div>';
		}
	}
}
