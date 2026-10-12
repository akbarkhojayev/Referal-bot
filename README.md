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
