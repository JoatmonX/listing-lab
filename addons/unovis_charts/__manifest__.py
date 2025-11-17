{
    'name': 'Unovis Charts (OWL Portal Wrapper)',
    'summary': 'Thin OWL wrapper to embed any Unovis chart in the Odoo user portal',
    'version': '19.0.1.0.0',
    'license': 'LGPL-3',
    'author': 'Code by Network',
    'website': 'https://codebynetwork.com',
    'category': 'Portal',
    'depends': ['web', 'portal'],
    'data': [],
    'assets': {
        'web.assets_frontend': [
            # Ensure Unovis is available: tries local global, otherwise falls back to CDN
            'unovis_charts/static/src/lib/unovis_loader.js',
            'unovis_charts/static/src/components/unovis_chart/unovis_chart.css',
            'unovis_charts/static/src/components/unovis_chart/unovis_chart.js',
        ],
        'web.assets_qweb': [
            'unovis_charts/static/src/components/unovis_chart/unovis_chart.xml',
        ],
    },
    # Using views/assets.xml to optionally inject Unovis UMD from CDN at runtime when not provided by the page.
    'installable': True,
}
