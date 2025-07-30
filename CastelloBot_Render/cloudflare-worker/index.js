export default {
  async fetch(request, env, ctx) {
    const response = await fetch("https://castellobot.onrender.com/healthz");
    return new Response(`Manual ping status: ${response.status}`);
  },

  async scheduled(event, env, ctx) {
    try {
      const response = await fetch("https://castellobot.onrender.com/healthz");
      console.log(`✅ Auto ping status: ${response.status}`);
    } catch (e) {
      console.error("❌ Ошибка при авто-пинге:", e);
    }
  }
}
