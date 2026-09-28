# FenixPortChecker — proje tanımı

Küçük bir Windows masaüstü aracı: PC’yi herhangi bir switch portuna taktığınızda **o portun VLAN / IP bilgisini** ve **o kablo üzerinde dönen trafiğin özetini** gösterir.

Bu depo bağımsız bir FenixPortChecker projesidir; kendi başına geliştirilir, paketlenir ve yayınlanır.

## Ne işe yarar

Sahada kabloyu takarsınız, uygulamayı açarsınız, bağlandığınız kartı seçip **Portu Tara** derseniz:

| Bilgi | Kaynak |
| --- | --- |
| Bu PC’nin IP / maske / ağ geçidi / DHCP / DNS | Windows ağ yığını |
| Kart VLAN kimliği (varsa) | sürücü / Hyper-V / Intel VLAN |
| Karşıdaki switch adı, port adı, yönetim IP, native VLAN | **LLDP** veya **CDP** (switch ilan ediyorsa) |
| Trunk ise görülen 802.1Q VLAN etiketleri | kablo üzerindeki etiketli kareler |
| Hangi protokol dönüyor (ARP, DHCP, DNS, HTTPS…) | bağlı olduğunuz yayın alanındaki kareler |
| En çok konuşan MAC / IP | aynı kare özeti |

Switch’e SSH/SNMP ile girmeden, **sadece bağlı olduğunuz portun gözünden** bakar. Switch’in diğer portlarındaki trafiği göremez; o bilgi için yönetim erişimi gerekir (v0.2).

## Ne değildir

- Switch’in tüm portlarını izleyen bir NetFlow/sFlow kolektörü değil.
- Yetkisiz erişim, exploit veya gizli dinleme aracı değil. Yalnızca bu PC’nin bağlı olduğu kabloyu, sizin başlattığınız oturumda özetler.
- LLDP/CDP kapalı bir switch’te komşu port adını uyduramaz. O durumda IP/VLAN ve trafik özeti hâlâ çalışır.

## Mimari (v0.1)

```
Windows MSI (Python gömülü, WebView2 penceresi)
        │
        ▼
┌───────────────────┐     ┌────────────────────┐
│  Keşif motoru     │────▶│  Masaüstü pencere  │
│  nic / lldp / cdp │     │  (pywebview +      │
│  802.1Q / trafik  │     │   yerel HTTP)      │
│  TCP yedek liste  │     └────────────────────┘
└───────────────────┘
```

- Dil: Python 3.11+
- Arayüz: yerel FastAPI + tek sayfa (koyu masaüstü teması)
- Paketleme hedefi: `run.bat` ile geliştirme; sonra PyInstaller EXE
- Linux’ta birim testleri ve Demo modu ile doğrulanır (Windows’a özel yakalama yolu ayrı doğrulanır)

## Sürüm planı

### v0.1 — bu sürüm (şimdi)

1. Adaptör listesi (Windows PowerShell / Linux sysfs)
2. Yerel IP, maske, geçit, DHCP, DNS, MAC
3. LLDP ve CDP karesi çözücü (switch, port, VLAN, yönetim IP)
4. 802.1Q VLAN etiketlerini toplama
5. Trafik özeti + son kare günlüğü + üst konuşmacılar
6. Donanım yokken UI’yi dolduran **Demo** modu
7. İsteğe bağlı salt-okunur SNMPv2c `sysName` / `sysDescr` sorgusu
8. **MSI masaüstü paketi** (Python kurulumu yok, WebView2 pencere)

### v0.2

- Npcap yoksa net uyarı ve kurulum linki
- SNMP ile MAC → port (`dot1dTpFdbPort`) ve port PVID
- Cisco/Huawei/Aruba `show` komut şablonları (SSH oturumu üzerinden)
- PyInstaller ile tek `FenixPortChecker.exe`
- Kart tak/çık olayını izleyip otomatik tarama

### v0.3

- Rapor dışa aktarma (HTML / JSON)
- Raporu snapshot olarak diske / cloud’a yazma

## Windows gereksinimleri

1. Python 3.11+ (`python.org`) veya ileride taşınabilir EXE
2. **Npcap** (LLDP/CDP ve L2 trafik için şart — Windows ham soketi 802.1AB karelerini vermez)
3. Uygulamayı **yönetici** olarak çalıştırmak genelde gerekir
4. Switch’te LLDP veya CDP açık olmalı (Cisco: `lldp run` / `cdp run`; Huawei: `lldp enable`).
   Instant On 1960 LLDP varsayılan açıktır; TX aralığı **30 sn** — kısa taramalar komşuyu kaçırır (uygulama ~35 sn dinler).
   Instant On CDP göndermez. Yönetim için mobil uygulama / portal veya yerel web UI (`192.168.1.1` / DHCP IP) kullanılır.

## Güvenlik notu

Dinleme yalnızca seçilen yerel ağ kartınadır. SNMP yalnızca sizin yazdığınız adrese, verdiğiniz community ile **GET** yapar. SET / tarama / brute-force yoktur.
