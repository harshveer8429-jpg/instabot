import os
import random
import string
import time
import logging
import threading
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '8100070394:AAE5Pov3SnkoV4It9Az2OE7_q3It36mEl50')
ADMIN_USER_ID = 6716174520  # Your user ID

# Conversation states
ACCOUNT_COUNT, PASSWORD, EMAIL_DOMAIN = range(3)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class InstagramAccountCreator:
    def __init__(self):
        self.created_accounts = []
        self.is_running = False
        self.current_data = {}
        self.total_requested = 0
        self.common_password = ""
        self.email_domain = ""
        self.creation_delay = 30  # 30 seconds delay between accounts
        
    def generate_username(self):
        """Generate random username"""
        letters = string.ascii_lowercase
        numbers = string.digits
        return ''.join(random.choice(letters + numbers) for i in range(8))
    
    def setup_driver(self):
        """Setup Chrome driver for Replit"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--remote-debugging-port=9222')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Use webdriver-manager for automatic driver management
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            return driver
        except Exception as e:
            logger.error(f"Driver setup failed: {e}")
            return None
    
    def create_instagram_account(self, email, username, password):
        """Create a single Instagram account"""
        driver = None
        try:
            driver = self.setup_driver()
            if not driver:
                return None
            
            # Navigate to Instagram signup
            driver.get("https://www.instagram.com/accounts/emailsignup/")
            
            wait = WebDriverWait(driver, 20)
            
            # Wait for page to load
            time.sleep(3)
            
            # Fill email/phone field
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "emailOrPhone")))
            email_field.clear()
            email_field.send_keys(email)
            
            # Fill full name field
            fullname_field = driver.find_element(By.NAME, "fullName")
            fullname_field.clear()
            fullname_field.send_keys(f"User {username}")
            
            # Fill username field
            username_field = driver.find_element(By.NAME, "username")
            username_field.clear()
            username_field.send_keys(username)
            
            # Fill password field
            password_field = driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(password)
            
            time.sleep(2)
            
            # Click signup button
            signup_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign up')]")
            driver.execute_script("arguments[0].click();", signup_button)
            
            # Wait for result
            time.sleep(5)
            
            # Check if signup was successful
            current_url = driver.current_url
            if "challenge" in current_url or "accounts/emailsignup" not in current_url:
                logger.info(f"✅ Account creation successful for {username}")
                return {
                    'username': username,
                    'password': password,
                    'email': email,
                    'status': 'success'
                }
            else:
                # Check for error messages
                try:
                    error_element = driver.find_element(By.ID, "ssfErrorAlert")
                    error_msg = error_element.text if error_element else "Unknown error"
                    logger.error(f"❌ Signup failed: {error_msg}")
                except:
                    logger.error("❌ Signup failed: Unknown error")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating account: {str(e)}")
            return None
        finally:
            if driver:
                driver.quit()
    
    def start_creation_process(self, num_accounts, common_password, email_domain, update, context):
        """Start the account creation process"""
        self.is_running = True
        self.created_accounts = []
        self.total_requested = num_accounts
        self.common_password = common_password
        self.email_domain = email_domain
        
        # Start in separate thread to avoid blocking
        thread = threading.Thread(
            target=self._create_accounts_thread, 
            args=(num_accounts, common_password, email_domain, update, context)
        )
        thread.start()
    
    def _create_accounts_thread(self, num_accounts, common_password, email_domain, update, context):
        """Thread function for account creation"""
        try:
            # Send start message
            start_message = (
                f"🚀 Starting creation of {num_accounts} Instagram accounts...\n\n"
                f"📧 Email Domain: {email_domain}\n"
                f"🔑 Password: {common_password}\n"
                f"⏱️ Delay: {self.creation_delay} seconds between accounts\n\n"
                f"⏳ Please wait, this may take a while..."
            )
            context.bot.send_message(chat_id=update.effective_chat.id, text=start_message)
            
            successful = 0
            failed = 0
            
            for i in range(num_accounts):
                if not self.is_running:
                    break
                
                # Generate account data
                username = self.generate_username()
                email = f"{username}{i+1}@{email_domain.replace('@', '')}"
                
                # Create account
                account = self.create_instagram_account(email, username, common_password)
                
                if account:
                    self.created_accounts.append(account)
                    successful += 1
                    
                    # Send immediate success notification
                    success_msg = (
                        f"✅ Account {i+1} Created Successfully!\n"
                        f"👤 Username: {account['username']}\n"
                        f"📧 Email: {account['email']}\n"
                        f"🔑 Password: {account['password']}"
                    )
                    context.bot.send_message(chat_id=update.effective_chat.id, text=success_msg)
                else:
                    failed += 1
                    context.bot.send_message(
                        chat_id=update.effective_chat.id, 
                        text=f"❌ Account {i+1} creation failed"
                    )
                
                # Send progress every 3 accounts
                if (i + 1) % 3 == 0:
                    progress_msg = f"📊 Progress: {i+1}/{num_accounts} | ✅ Successful: {successful} | ❌ Failed: {failed}"
                    context.bot.send_message(chat_id=update.effective_chat.id, text=progress_msg)
                
                # 30-second delay between creations (as requested)
                if i < num_accounts - 1:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id, 
                        text=f"⏱️ Waiting {self.creation_delay} seconds before next account..."
                    )
                    time.sleep(self.creation_delay)
            
            # Send final results
            self.send_final_results(update, context, successful, failed)
            
        except Exception as e:
            error_msg = f"❌ Error during account creation: {str(e)}"
            context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)
    
    def send_final_results(self, update, context, successful, failed):
        """Send final results"""
        try:
            result_message = f"🎉 ACCOUNT CREATION COMPLETED!\n\n"
            result_message += f"📊 Final Statistics:\n"
            result_message += f"✅ Successful: {successful}\n"
            result_message += f"❌ Failed: {failed}\n"
            if (successful + failed) > 0:
                result_message += f"📈 Success Rate: {(successful/(successful+failed))*100:.1f}%\n\n"
            else:
                result_message += f"📈 Success Rate: 0%\n\n"
            
            if self.created_accounts:
                result_message += "📝 CREATED ACCOUNTS:\n\n"
                for i, account in enumerate(self.created_accounts, 1):
                    result_message += f"🔹 Account {i}:\n"
                    result_message += f"   👤 Username: {account['username']}\n"
                    result_message += f"   📧 Email: {account['email']}\n"
                    result_message += f"   🔑 Password: {account['password']}\n"
                    result_message += f"   ━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            context.bot.send_message(chat_id=update.effective_chat.id, text=result_message)
            
        except Exception as e:
            context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"❌ Error sending results: {str(e)}"
            )
    
    def get_total_summary(self):
        """Get total accounts summary in requested format"""
        if not self.created_accounts:
            return "📊 No accounts created yet."
        
        summary = f"total account {self.total_requested}\n\n"
        
        for i, account in enumerate(self.created_accounts, 1):
            summary += f"{i}total account according to user input\n"
            summary += f"password: {account['password']}\n"
            summary += f"username: {account['username']}\n"
            summary += f"email: {account['email']}\n"
            summary += "━" * 30 + "\n"
        
        return summary

# Initialize the creator
creator = InstagramAccountCreator()

# Admin check decorator
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != ADMIN_USER_ID:
            await update.message.reply_text("🚫 Access Denied. Admin only.")
            return ConversationHandler.END
        return await func(update, context, *args, **kwargs)
    return wrapper

@admin_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    welcome_text = """
🤖 **Instagram Account Creator Bot**

🚀 **Ready to create real Instagram accounts!**

**Commands:**
/create - Start creating accounts
/status - Check current status  
/stop - Stop creation process
/total - Show all created accounts

**Features:**
⏱️ 30-second delay between accounts
📊 Real-time progress updates
🔐 Secure account creation

⚠️ **Note:** Uses real Instagram signup process
    """
    await update.message.reply_text(welcome_text)
    return ConversationHandler.END

@admin_only  
async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start account creation process"""
    if creator.is_running:
        await update.message.reply_text("⚠️ Creation already in progress. Use /stop to cancel.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔢 How many Instagram accounts do you want to create?\n"
        "(Recommended: 1-10 for better success rate)\n\n"
        "⏱️ Note: 30-second delay between each account"
    )
    return ACCOUNT_COUNT

async def get_account_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get number of accounts to create"""
    try:
        num_accounts = int(update.message.text)
        if num_accounts <= 0 or num_accounts > 50:
            await update.message.reply_text("❌ Please enter a number between 1-50")
            return ACCOUNT_COUNT
        
        context.user_data['num_accounts'] = num_accounts
        await update.message.reply_text(
            f"🔑 Enter a common password for all {num_accounts} accounts:\n"
            "(Minimum 6 characters)"
        )
        return PASSWORD
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number")
        return ACCOUNT_COUNT

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get common password"""
    password = update.message.text.strip()
    
    if len(password) < 6:
        await update.message.reply_text("❌ Password must be at least 6 characters")
        return PASSWORD
    
    context.user_data['password'] = password
    await update.message.reply_text(
        "📧 Enter email domain for all accounts:\n"
        "Example: gmail.com, yahoo.com, outlook.com"
    )
    return EMAIL_DOMAIN

async def get_email_domain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get email domain and start creation"""
    email_domain = update.message.text.strip()
    
    if '.' not in email_domain or ' ' in email_domain:
        await update.message.reply_text("❌ Please enter a valid email domain")
        return EMAIL_DOMAIN
    
    # Get data from context
    num_accounts = context.user_data['num_accounts']
    password = context.user_data['password']
    
    # Start creation process
    await update.message.reply_text("🔄 Starting account creation process...")
    creator.start_creation_process(num_accounts, password, email_domain, update, context)
    
    context.user_data.clear()
    return ConversationHandler.END

@admin_only
async def total_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all created accounts in requested format"""
    summary = creator.get_total_summary()
    await update.message.reply_text(f"```\n{summary}\n```", parse_mode='MarkdownV2')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check creation status"""
    if creator.is_running:
        status_msg = (
            f"🔄 Account creation in progress...\n"
            f"📊 Created so far: {len(creator.created_accounts)} accounts\n"
            f"⏱️ Delay: {creator.creation_delay} seconds between accounts\n"
            f"⚡ Bot is running on Replit"
        )
    else:
        status_msg = "✅ No active account creation process"
    
    await update.message.reply_text(status_msg)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop creation process"""
    if creator.is_running:
        creator.is_running = False
        await update.message.reply_text("🛑 Account creation stopped")
    else:
        await update.message.reply_text("❌ No active process to stop")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation"""
    context.user_data.clear()
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('create', create_command)],
        states={
            ACCOUNT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_account_count)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            EMAIL_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email_domain)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("total", total_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(conv_handler)
    
    # Start bot
    print("🤖 Instagram Account Creator Bot Started on Replit!")
    print("⏱️ 30-second delay between accounts enabled")
    print("🚀 Ready to create real Instagram accounts...")
    application.run_polling()

if __name__ == "__main__":
    main()