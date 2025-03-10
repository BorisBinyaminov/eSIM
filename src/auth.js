// auth.js
const authService = {
  /**
   * Sends Telegram initData to the back-end for verification.
   * Returns a Promise resolving to an object like:
   * { success: true, user: { id, username, photo_url } }
   */
  authenticateTelegram: async (initData) => {
    try {
      const response = await fetch("/auth/telegram", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ initData })
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error in authenticateTelegram:", error);
      throw error;
    }
  },

  /**
   * Calls the logout endpoint.
   */
  logoutTelegram: async () => {
    try {
      const response = await fetch("/auth/logout", {
        method: "POST"
      });
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error in logoutTelegram:", error);
      throw error;
    }
  }
};

export default authService;
