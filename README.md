# FenixPortChecker

PC’yi switch portuna taktığınızda o portun **VLAN / IP** bilgisini ve kablo üzerindeki **trafik özetini** gösteren Windows masaüstü aracı.

## Kurulum (EXE / MSI — Python gerekmez)

GitHub Actions `Build FenixPortChecker Windows EXE and MSI` işinden her iki artefaktı da indirin:

- `FenixPortChecker-0.1.1-exe` → taşınabilir `FenixPortChecker.exe`
- `FenixPortChecker-0.1.1-msi` → kurulum paketi `FenixPortChecker-0.1.1.msi`

**MSI:** çift tıklayıp kurun; Başlat menüsü veya masaüstündeki **FenixPortChecker** kısayolunu açın. Kaldırmak için Windows → Uygulamalar → FenixPortChecker.

**EXE:** indirdiğiniz dosyayı doğrudan çalıştırın (kurulum gerekmez).

Kartı seçip **Portu Tara**. Switch yoksa **Demo** kutusunu işaretleyin.

LLDP/CDP (karşıdaki switch adı ve port) için isteğe bağlı [Npcap](https://npcap.com/). IP, VLAN ve açık TCP bağlantıları Npcap olmadan da gelir.

## Geliştirme (Python)

```bat
git clone https://github.com/yavuzyeni-rgb/fenixportchecker.git
cd fenixportchecker
run.bat
```

```bash
git clone https://github.com/yavuzyeni-rgb/fenixportchecker.git
cd fenixportchecker
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m portgozu --no-browser
PYTHONPATH=src python3 -m pytest -q
```

Windows’ta EXE + MSI üretmek: `packaging/build-windows.ps1` (Windows + Python 3.12 + .NET 8 SDK). Anka logosu: `packaging/anka-icon.png` → `packaging/portgozu.ico` (EXE/MSI); arayüzde `static/favicon.svg`.

Ayrıntılı kapsam: [PROJE.md](PROJE.md)
