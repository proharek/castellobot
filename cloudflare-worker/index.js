export default {
  async scheduled(event, env, ctx) {
    console.log("✅ Cron triggered, pinging bot...");
    try {
      const response = await fetch("https://38830963-534c-403b-9ec1-a15113d21b13-00-1oo4rn2lkznb5.janeway.replit.dev");
      console.log(`Response status: ${response.status}`);
    } catch (e) {
      console.error("Ошибка при пинге бота:", e);
    }
  }
}
