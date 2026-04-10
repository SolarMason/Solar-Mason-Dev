#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Solar Mason — Datasheet Downloader
# Run this script from the datasheets/ directory to download all
# manufacturer datasheets. Requires curl and internet access.
# ═══════════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")"
mkdir -p panels inverters racking battery

echo "═══ Downloading manufacturer datasheets ═══"
echo ""

# ─── ENPHASE INVERTERS ───────────────────────────────────────
echo "⚡ Enphase..."
curl -sL "https://enphase.com/download/iq8-series-microinverters-data-sheet" -o inverters/enphase-iq8-series-residential.pdf 2>/dev/null && echo "  ✅ IQ8 Series Residential" || echo "  ❌ IQ8 Series — try: https://enphase.com/download/iq8-series-microinverters-data-sheet"
curl -sL "https://enphase.com/download/iq8-commercial-microinverters-data-sheet" -o inverters/enphase-iq8-commercial.pdf 2>/dev/null && echo "  ✅ IQ8 Commercial" || echo "  ❌ IQ8 Commercial — try: https://enphase.com/download/iq8-commercial-microinverters-data-sheet"
curl -sL "https://enphase.com/download/iq-battery-5p-data-sheet" -o battery/enphase-iq-battery-5p.pdf 2>/dev/null && echo "  ✅ IQ Battery 5P" || echo "  ❌ IQ Battery 5P — try: https://enphase.com/download/iq-battery-5p-data-sheet"

# ─── SOLAREDGE INVERTERS ─────────────────────────────────────
echo "⚡ SolarEdge..."
curl -sL "https://www.solaredge.com/us/sites/default/files/se-single-phase-HD-wave-inverter-datasheet.pdf" -o inverters/solaredge-hd-wave-single-phase.pdf 2>/dev/null && echo "  ✅ HD-Wave Single Phase" || echo "  ❌ HD-Wave — visit: https://www.solaredge.com/us/products/residential"
curl -sL "https://www.solaredge.com/us/sites/default/files/se-p-series-add-on-power-optimizer-datasheet.pdf" -o inverters/solaredge-p-series-optimizer.pdf 2>/dev/null && echo "  ✅ P-Series Optimizer" || echo "  ❌ P-Series — visit: https://www.solaredge.com/us/products/power-optimizers"
curl -sL "https://www.solaredge.com/us/sites/default/files/se-s-series-power-optimizer-datasheet.pdf" -o inverters/solaredge-s-series-optimizer.pdf 2>/dev/null && echo "  ✅ S-Series Optimizer" || echo "  ❌ S-Series — visit: https://www.solaredge.com/us/products/power-optimizers"

# ─── QCELLS PANELS ───────────────────────────────────────────
echo "☀️ Qcells..."
curl -sL "https://qcells.com/us/get-started/complete-energy-solutions/solar-panels-pdf-download/q-tron-blk-m-g2-plus" -o panels/qcells-qtron-blk-m-g2-plus.pdf 2>/dev/null && echo "  ✅ Q.TRON BLK M-G2+" || echo "  ❌ Q.TRON — visit: https://qcells.com/us/solar-panels"
curl -sL "https://qcells.com/us/get-started/complete-energy-solutions/solar-panels-pdf-download/q-peak-duo-blk-ml-g10-plus" -o panels/qcells-qpeak-duo-blk-ml-g10-plus.pdf 2>/dev/null && echo "  ✅ Q.PEAK DUO BLK ML-G10+" || echo "  ❌ Q.PEAK DUO — visit: https://qcells.com/us/solar-panels"

# ─── REC PANELS ──────────────────────────────────────────────
echo "☀️ REC..."
curl -sL "https://www.recgroup.com/sites/default/files/documents/ds_rec_alpha_pure-r_series_en.pdf" -o panels/rec-alpha-pure-r.pdf 2>/dev/null && echo "  ✅ Alpha Pure-R" || echo "  ❌ Alpha Pure-R — visit: https://www.recgroup.com/en/products"
curl -sL "https://www.recgroup.com/sites/default/files/documents/ds_rec_alpha_pure-rx_series_en.pdf" -o panels/rec-alpha-pure-rx.pdf 2>/dev/null && echo "  ✅ Alpha Pure-RX" || echo "  ❌ Alpha Pure-RX — visit: https://www.recgroup.com/en/products"

# ─── CANADIAN SOLAR ──────────────────────────────────────────
echo "☀️ Canadian Solar..."
curl -sL "https://www.canadiansolar.com/wp-content/uploads/2024/06/CS6R-MS_v5.72.pdf" -o panels/canadian-solar-hiku6.pdf 2>/dev/null && echo "  ✅ HiKu6 CS6R" || echo "  ❌ HiKu6 — visit: https://www.canadiansolar.com/residential-solar-panels/"
curl -sL "https://www.canadiansolar.com/wp-content/uploads/2024/09/CS7N-TB_v5.73.pdf" -o panels/canadian-solar-topbihiku7.pdf 2>/dev/null && echo "  ✅ TOPBiHiKu7" || echo "  ❌ TOPBiHiKu7 — visit: https://www.canadiansolar.com/commercial-solar-panels/"

# ─── JINKO SOLAR ─────────────────────────────────────────────
echo "☀️ Jinko Solar..."
curl -sL "https://www.jinkosolar.com/uploads/JKM425-445N-54HL4R-BDV-F1-EN.pdf" -o panels/jinko-tiger-neo-54hl4r.pdf 2>/dev/null && echo "  ✅ Tiger Neo 54HL4R" || echo "  ❌ Tiger Neo — visit: https://www.jinkosolar.com/en/site/tigerneo"

# ─── TRINA SOLAR ─────────────────────────────────────────────
echo "☀️ Trina Solar..."
curl -sL "https://static.trinasolar.com/sites/default/files/PS-M-0683_Datasheet_Vertex_S_Plus_NEG9R.28_EN.pdf" -o panels/trina-vertex-s-plus.pdf 2>/dev/null && echo "  ✅ Vertex S+" || echo "  ❌ Vertex S+ — visit: https://www.trinasolar.com/en-us/product/vertex-s-plus"

# ─── JA SOLAR ────────────────────────────────────────────────
echo "☀️ JA Solar..."
curl -sL "https://www.jasolar.com/uploadfile/2024/0522/JAM54D41_445-470_LB_EN.pdf" -o panels/ja-solar-deepblue-4-pro.pdf 2>/dev/null && echo "  ✅ DeepBlue 4.0 Pro" || echo "  ❌ DeepBlue 4.0 — visit: https://www.jasolar.com/html/en/products/"

# ─── LONGI ───────────────────────────────────────────────────
echo "☀️ LONGi..."
curl -sL "https://www.longi.com/en/products/modules/hi-mo-x6/" -o panels/longi-hi-mo-x6.pdf 2>/dev/null && echo "  ✅ Hi-MO X6" || echo "  ❌ Hi-MO X6 — visit: https://www.longi.com/en/products/modules/"

# ─── SILFAB ──────────────────────────────────────────────────
echo "☀️ Silfab..."
curl -sL "https://silfabsolar.com/wp-content/uploads/2024/Silfab_Prime_NTC_Datasheet.pdf" -o panels/silfab-prime-ntc.pdf 2>/dev/null && echo "  ✅ Prime NTC" || echo "  ❌ Prime NTC — visit: https://silfabsolar.com/products/"

# ─── IRONRIDGE RACKING ───────────────────────────────────────
echo "🔧 IronRidge..."
curl -sL "https://www.ironridge.com/wp-content/uploads/2024/01/XR100-Rail-Spec-Sheet.pdf" -o racking/ironridge-xr100-spec.pdf 2>/dev/null && echo "  ✅ XR100" || echo "  ❌ XR100 — visit: https://www.ironridge.com/products/xr100-rail/"
curl -sL "https://www.ironridge.com/wp-content/uploads/2024/01/XR1000-Rail-Spec-Sheet.pdf" -o racking/ironridge-xr1000-spec.pdf 2>/dev/null && echo "  ✅ XR1000" || echo "  ❌ XR1000 — visit: https://www.ironridge.com/products/xr1000-rail/"

echo ""
echo "═══ Download complete ═══"
echo "Files saved to: $(pwd)"
echo ""
echo "NOTE: Some manufacturer URLs may redirect to login pages or change over time."
echo "If a download failed (❌), visit the URL manually and save the PDF to the"
echo "appropriate directory (panels/, inverters/, racking/, battery/)."
ls -R | head -40
