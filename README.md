# Referal ovoz yig'ish boti (aiogram 3)

## Ishga tushirish
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # BOT_TOKEN va ADMIN_IDS ni yozing
./venv/bin/python bot.py
```

## Admin
`/start` yoki `/admin` — admin panel:
- ➕ Guruh qo'shish / 📋 Guruhlar (ovozlar, top taklifchilar, o'chirish)
- ➕ Kanal qo'shish / 📢 Kanallar — majburiy obuna shartlari (bot kanalda admin bo'lishi kerak)
- 📈 Statistika, ✉️ Xabar yuborish (hammaga)

## Foydalanuvchi
1. `/start` → majburiy kanallarga a'zo bo'ladi → **✅ Tekshirish**
2. Guruhni tanlab ovoz beradi (har bir user faqat 1 marta)
3. O'z referal linkini oladi: `t.me/bot?start=r<user_id>`
4. Shu link orqali kelgan odam shartlarni bajarsa, ovozi avtomatik **taklif qilgan odamning guruhiga** tushadi
5. Guruh linki `t.me/bot?start=g<group_id>` — to'g'ridan-to'g'ri shu guruhga ovoz

## Qo'shimcha qoidalar
- Kamida 1 ta majburiy kanal bo'lsa, kanallar tagida doim **📸 Instagram** linki chiqadi (`.env` dagi `INSTAGRAM_URL`).
- Majburiy kanaldan chiqib ketgan odamning ovozi **-1** bo'ladi; unga va uni taklif qilgan odamga xabar boradi.
  Qayta a'zo bo'lib `/start` bossa, ovozi o'sha guruhga qaytadi.

## Barqaror ishlash va tekshirish
- Xatolar foydalanuvchiga o‘zbekcha ko‘rsatiladi; texnik tafsilotlar logda qoladi.
- Telegram obunani tekshira olmaganida mavjud ovoz bekor qilinmaydi.
- Bir foydalanuvchining parallel so‘rovlari ketma-ket ishlanadi; takroriy ovoz bazada bloklanadi.
- Telegram tezlik limitida so‘rov qayta yuboriladi. Aloqa uzilsa polling qayta ulanadi.
- Bot qayta ishga tushganda kutilayotgan Telegram yangilanishlari o‘chirilmaydi.
- Adminning tugallanmagan kiritish holati xotirada saqlanadi; restartdan keyin amalni qayta boshlang.
- Bir token bilan faqat bitta bot jarayonini ishga tushiring.

Testlar haqiqiy `bot.db` o‘rniga vaqtinchalik bazada ishlaydi:
```bash
./venv/bin/python -m unittest discover -s tests -v
```

Kompyuter yoki server yoqilgan paytda bot jarayoni kutilmaganda to‘xtasa avtomatik qayta ishga tushirish uchun `deploy/referral-bot.service` namunasi bor. Fayldagi loyiha va Python yo‘llarini serverga moslang, keyin Linux foydalanuvchi xizmati sifatida o‘rnating:
```bash
mkdir -p ~/.config/systemd/user
cp deploy/referral-bot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now referral-bot
journalctl --user -u referral-bot -f
```
Bu xizmat hozircha avtomatik o‘rnatilmagan. Doimiy ishlash uchun server doim yoqilgan, interneti faol bo‘lishi va foydalanuvchi systemd menejeri ishlashi kerak. Elektr, internet yoki Telegram uzilishlari paytida uzluksiz xizmatni kafolatlab bo‘lmaydi.

`.env` va `bot.db` maxfiy ma’lumot hisoblanadi. `.gitignore` yangi fayllarni Gitga qo‘shishdan saqlaydi, lekin avval kuzatuvga olingan fayllarni Git tarixidan olib tashlamaydi. Avval repozitoriyga tushgan bot tokenini BotFather orqali yangilang. Haqiqiy tokenni `.env.example` ichiga yozmang.
