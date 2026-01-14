export default async function handler(req, res) {
    if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

    const botToken = "8577863218:AAH1SSBgHjb2cc7eyMRNjp_kn_dpckSdGzQ"; // Token Anda
    const myChatId = "7981083332"; // Chat ID Anda
    const { message } = req.body;

    try {
        await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: myChatId,
                text: message,
                parse_mode: "Markdown"
            })
        });
        return res.status(200).json({ status: 'ok' });
    } catch (error) {
        return res.status(500).json({ error: error.message });
    }
}
