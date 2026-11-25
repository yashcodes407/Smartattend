SMARTATTEND - WINDOWS 11 QUICK START

1) Python 3 install karein: https://www.python.org/downloads/
   Installer khulte waqt "Add Python to PATH" checkbox zaroor tick karein.
2) Is folder ko extract karein (ZIP par right click > Extract All).
3) run_smartattend.bat par double-click karein.
4) Pehli baar packages install honge; internet on rakhein.
5) Browser mein http://127.0.0.1:5000 khulega.

DEMO LOGIN:
Username: teacher
Password: 1234

DEMO KARNE KA TARIKA:
1. Students > Add Student: Roll, Name, Class bharein.
2. Student save hote hi QR code page khulega. QR ko phone par dikhayein ya PNG download/print karein.
3. Scan QR par jaakar laptop webcam allow karein.
4. QR ko camera ke saamne rakhein. Successful scan par attendance message aayega.
5. Attendance page par aaj ka record dekhein; CSV export bhi kar sakte hain.

IMPORTANT:
- QR scanner browser mein camera access use karta hai. Localhost par browser camera access aam taur par allowed hota hai.
- QR scan ke liye internet chahiye kyunki scanner library CDN se load hoti hai.
- Agar laptop camera available nahi hai, QR scanner ke bajay phone par QR image dikhakar webcam se scan karein, ya practical ke liye QR page + attendance records ka workflow dikhayein.
- Ye college practical ke liye demo prototype hai; real deployment se pehle proper authentication, HTTPS, backups aur security hardening zaroori hain.
- Database smartattend.db isi folder mein automatic banegi. Folder delete karne se records delete ho jayenge.
