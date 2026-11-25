async function pageFunction(context) {
    const { jQuery: $, request, log } = context;
    const url = request.url;

    let supermercado = 'Desconocido';
    if (url.includes('carrefour')) supermercado = 'Carrefour';
    else if (url.includes('supermercadosdia')) supermercado = 'DIA';
    else if (url.includes('vea')) supermercado = 'Cencosud (Vea)';
    else if (url.includes('lacoopeencasa')) supermercado = 'Cooperativa Obrera';

    const limpiarPrecio = (texto) => {
        if (!texto) return null;
        const match = texto.match(/\$?\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{1,2})?)/);
        if (!match) return null;
        return parseFloat(match[1].replace(/\./g, '').replace(',', '.')) || null;
    };

    // Scroll real dentro de la página para disparar la carga lazy
    const scrollear = async (veces, pausaMs) => {
        for (let i = 0; i < veces; i++) {
            window.scrollBy(0, 800);
            await context.waitFor(pausaMs);
        }
        window.scrollTo(0, 0);
    };

    // =====================================================
    // ESPERAS Y SCROLL (todos los sitios)
    // =====================================================
    await context.waitFor('article, [class*="product-summary"], [class*="carrefourar"], [class*="galleryItem"], [class*="producto"]', { timeout: 25000 }).catch(() => { });

    if (supermercado !== 'Cooperativa Obrera') {
        await scrollear(supermercado === 'Carrefour' ? 6 : 4, 1200);
    }
    await context.waitFor(supermercado === 'Carrefour' ? 5000 : 3000);

    const productos = [];
    const vistos = new Set();

    // =====================================================
    // 1. Tiendas VTEX por HTML (Carrefour, DIA, Vea)
    // =====================================================
    if (['Carrefour', 'DIA', 'Cencosud (Vea)'].includes(supermercado)) {
        let cards = $('[class*="product-summary"]');
        if (cards.length === 0) cards = $('article');
        if (cards.length === 0) cards = $('[class*="galleryItem"]');
        if (cards.length === 0 && supermercado === 'Carrefour') {
            cards = $('[class*="carrefourar-search-result"] > div > div, [class*="vtex-flex-layout"] [class*="stretchChildrenWidth"]').filter((_, e) => $(e).text().includes('$') && $(e).find('img').length > 0 && $(e).text().length < 500);
        }

        cards.each((index, el) => {
            const card = $(el);
            const marca = card.find('[class*="productBrand"]').first().text().trim();
            const nombre = card.find('[class*="productName"], h3, h2, [class*="name"]').first().text().trim();
            const descripcion = (marca && nombre && !nombre.includes(marca)) ? `${marca} ${nombre}` : (nombre || marca);

            const bloquesPrecio = card.find('[class*="sellingPrice"], [class*="listPrice"], [class*="currencyContainer"], [class*="price"], [class*="valtech-carrefourar-product-price"]')
                .filter((_, e) => !/kg|lt|litro|impuesto|nacional|x\s*1/i.test($(e).text()));

            let nums = [];
            bloquesPrecio.each((_, e) => {
                const val = limpiarPrecio($(e).text());
                if (val && val > 50) nums.push(val);
            });

            if (nums.length === 0) {
                const textoSinImpuestos = card.text().split(/Precio sin impuestos|x\s*1\s*(kg|lt|l)/i)[0];
                const rawMatches = textoSinImpuestos.match(/\$\s*[0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{1,2})?/g) || [];
                nums = rawMatches.map(limpiarPrecio).filter(n => n && n > 50);
            }

            const precioLista = nums.length > 0 ? Math.max(...nums) : null;
            const precioPromo = nums.length > 1 ? Math.min(...nums) : null;

            const claveUnica = `${descripcion}_${precioLista}`;
            if (descripcion && precioLista && !vistos.has(claveUnica)) {
                vistos.add(claveUnica);
                productos.push({
                    supermercado,
                    id_producto: `${supermercado}_${productos.length}_${descripcion.substring(0, 15)}`,
                    descripcion,
                    precio_lista: precioLista,
                    precio_referencia: precioLista,
                    precio_promo: precioPromo && precioPromo < precioLista ? precioPromo : null
                });
            }
        });
    }

    // =====================================================
    // 2. Cooperativa Obrera (Angular)
    // =====================================================
    else if (supermercado === 'Cooperativa Obrera') {
        $('[class*="producto"], [class*="card"]').each((index, el) => {
            const card = $(el);
            const textoCompleto = card.text().replace(/\s+/g, ' ').trim();
            if (!textoCompleto.includes('$') || textoCompleto.length > 450 || textoCompleto.length < 15) return;

            const descripcion = card.find('h2, h3, h4, p, span, a')
                .filter((_, e) => {
                    const t = $(e).text().trim();
                    return t.length > 10 && !t.includes('$') && !/precio|impuesto|regular|agregar|comprar|oferta|promo/i.test(t);
                })
                .first().text().trim();

            const textoSinImpuestos = textoCompleto.split(/Precio s\/impuestos/i)[0];
            const preciosEncontrados = textoSinImpuestos.match(/\$\s*[0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{1,2})?/g) || [];
            const nums = preciosEncontrados.map(limpiarPrecio).filter(n => n && n > 50);

            const precioReal = nums.length > 0 ? Math.min(...nums) : null;
            const precioReferencia = nums.length > 1 ? Math.max(...nums) : precioReal;

            const claveUnica = `${descripcion}_${precioReal}`;
            if (descripcion && precioReal && !vistos.has(claveUnica)) {
                vistos.add(claveUnica);
                productos.push({
                    supermercado,
                    id_producto: `Coop_${productos.length}_${descripcion.substring(0, 15)}`,
                    descripcion,
                    precio_lista: precioReal,
                    precio_referencia: precioReferencia,
                    precio_promo: null
                });
            }
        });
    }

    log.info(`${supermercado}: ${productos.length} productos extraídos de ${url}`);
    return productos;
}