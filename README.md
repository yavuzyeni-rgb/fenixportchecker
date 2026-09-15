# FenixPortChecker

PC’yi switch portuna taktığınızda o portun **VLAN / IP** bilgisini ve kablo üzerindeki **trafik özetini** gösteren Windows masaüstü aracı.

## Kurulum (MSI — Python gerekmez)

GitHub Actions `Build FenixPortChecker Windows MSI` işinden `FenixPortChecker-0.1.1.msi` dosyasını indirin.

1. MSI’ye çift tıklayın, kurun.
2. Başlat menüsü veya masaüstündeki **FenixPortChecker** kısayolunu açın.
3. Kartı seçip **Portu Tara**. Switch yoksa **Demo** kutusunu işaretleyin.

Kaldırmak için Windows → Uygulamalar → FenixPortChecker.

LLDP/CDP (karşıdaki switch adı ve port) için isteğe bağlı [Npcap](https://npcap.com/). IP, VLAN ve açık TCP bağlantıları Npcap olmadan da gelir.

## Geliştirme (Python)

```bat
cd Testler\FenixPortChecker
run.bat
```

```bash
cd Testler/FenixPortChecker
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m portgozu --no-browser
PYTHONPATH=src python3 -m pytest -q
```

Windows’ta MSI üretmek: `packaging/build-windows.ps1` (Windows + Python 3.12 + .NET 8 SDK).

Ayrıntılı kapsam: [PROJE.md](PROJE.md)
