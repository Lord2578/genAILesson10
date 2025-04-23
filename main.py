import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class FacebookPropertyScraper:
    def __init__(self, target_url, output_filename="facebook_posts.jsonl"):
        """Ініціалізація скрапера для сторінки нерухомості"""
        self.target_url = target_url
        self.output_filename = output_filename
        self.driver = None
        self.setup_browser()
        
    def setup_browser(self):
        """Налаштування браузера Chrome для скрапінгу"""
        browser_options = Options()
        # browser_options.add_argument("--headless")  # Закоментовано для наочності
        browser_options.add_argument("--disable-notifications")
        browser_options.add_argument("--window-size=1920,1080")
        browser_options.add_argument("--disable-extensions")
        browser_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.driver = webdriver.Chrome(options=browser_options)
        self.driver.implicitly_wait(5)
    
    def dismiss_login_popup(self):
        """Закриття діалогового вікна входу, якщо воно з'явилося"""
        try:
            print("Перевірка наявності діалогового вікна входу...")
            wait = WebDriverWait(self.driver, 6)
            close_buttons = wait.until(
                EC.any_of(
                    EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Закрити']")),
                    EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Close']"))
                )
            )
            
            close_buttons.click()
            print("✅ Діалогове вікно входу закрито")
            time.sleep(1)
        except (TimeoutException, Exception) as e:
            print(f"ℹ️ Діалогове вікно не виявлено або не вдалося закрити: {str(e)}")
    
    def load_more_content(self, scroll_count=6):
        """Прокрутка сторінки для завантаження додаткового контенту"""
        print(f"Завантаження додаткового контенту ({scroll_count} прокруток)...")
        
        for i in range(scroll_count):
            self.driver.execute_script(
                "window.scrollTo(0, document.documentElement.scrollHeight);"
            )
            print(f"Прокрутка {i+1}/{scroll_count}...")
            time.sleep(2.5)  # Пауза між прокрутками
    
    def extract_property_posts(self, max_posts=15):
        """Витягування даних з постів про нерухомість"""
        print("Пошук постів на сторінці...")
        
        # Різні XPath-селектори для пошуку постів
        post_selectors = [
            "//div[contains(@class, 'x1yztbdb')]",
            "//div[contains(@class, 'x1lliihq')]",
            "//div[contains(@class, 'xyamay9') and contains(@class, 'xqcrz7y')]"
        ]
        
        # Спробуємо різні селектори
        post_elements = []
        for selector in post_selectors:
            post_elements = self.driver.find_elements(By.XPATH, selector)
            if post_elements:
                print(f"Знайдено {len(post_elements)} постів за селектором: {selector}")
                break
        
        if not post_elements:
            print("❗ Не вдалося знайти жодного поста. Можливо, структура сторінки змінилася.")
            return []
        
        # Обмеження кількості постів для обробки
        post_elements = post_elements[:max_posts]
        
        # Список для зберігання даних про пости
        property_data = []
        
        for idx, post in enumerate(post_elements):
            print(f"Обробка поста {idx+1}/{len(post_elements)}...")
            
            post_info = {
                "post_url": "URL not found",
                "content": "No content found",
                "date": "Date not found"
            }
            
            # Витягування URL поста
            try:
                # Спробуємо знайти посилання з різними шляхами
                links = post.find_elements(By.XPATH, ".//a[contains(@href, '/posts/') or contains(@href, '/photos/')]")
                for link in links:
                    href = link.get_attribute('href')
                    if href and ('/posts/' in href or '/photos/' in href):
                        # Видалення параметрів URL
                        post_info["post_url"] = href.split('?')[0]
                        break
            except Exception as e:
                print(f"  Помилка при отриманні URL: {str(e)}")
            
            # Витягування тексту поста
            try:
                # Спробуємо різні селектори для пошуку тексту
                text_selectors = [
                    ".//div[@data-ad-comet-preview='message']//div[@dir='auto']",
                    ".//div[contains(@class, 'xdj266r')]//div[@dir='auto']",
                    ".//div[contains(@class, 'x1iorvi4')]//span"
                ]
                
                for selector in text_selectors:
                    text_elements = post.find_elements(By.XPATH, selector)
                    if text_elements:
                        post_info["content"] = text_elements[0].text.strip()
                        break
            except Exception as e:
                print(f"  Помилка при отриманні тексту: {str(e)}")
            
            # Витягування дати публікації
            try:
                # Спробуємо різні селектори для пошуку дати
                date_selectors = [
                    ".//span[contains(@class, 'x4k7w5x')]",
                    ".//span[contains(@class, 'xzsf02u')]",
                    ".//a[contains(@class, 'x1i10hfl')]//span[1]"
                ]
                
                for selector in date_selectors:
                    date_elements = post.find_elements(By.XPATH, selector)
                    if date_elements:
                        post_info["date"] = date_elements[0].text.strip()
                        break
            except Exception as e:
                print(f"  Помилка при отриманні дати: {str(e)}")
            
            # Додаємо дані поста до списку, якщо є URL або текст
            if post_info["post_url"] != "URL not found" or post_info["content"] != "No content found":
                property_data.append(post_info)
                print(f"  ✅ Дані поста додано: {post_info['content'][:30]}...")
        
        return property_data
    
    def save_data_to_file(self, data):
        """Збереження даних у JSONL файл"""
        if not data:
            print("❗ Немає даних для збереження")
            return
        
        try:
            with open(self.output_filename, 'w', encoding='utf-8') as f:
                for item in data:
                    json.dump(item, f, ensure_ascii=False)
                    f.write('\n')
            
            print(f"✅ Дані збережено у файл: {self.output_filename}")
            print(f"   Збережено {len(data)} записів")
        except Exception as e:
            print(f"❗ Помилка при збереженні даних: {str(e)}")
    
    def run(self, max_posts=15):
        """Запуск процесу скрапінгу"""
        try:
            print(f"🚀 Початок скрапінгу: {self.target_url}")
            
            # Відкриваємо цільову сторінку
            self.driver.get(self.target_url)
            print("✅ Сторінка завантажена")
            time.sleep(4)  # Чекаємо на повне завантаження
            
            # Закриваємо попап входу, якщо він з'явився
            self.dismiss_login_popup()
            
            # Прокручуємо для завантаження більшої кількості постів
            self.load_more_content()
            
            # Отримуємо дані з постів
            posts_data = self.extract_property_posts(max_posts)
            
            # Зберігаємо дані у файл
            self.save_data_to_file(posts_data)
            
            print("🏁 Скрапінг завершено успішно")
            
        except Exception as e:
            print(f"❗ Помилка при скрапінгу: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                print("🔒 Браузер закрито")


if __name__ == "__main__":
    # Налаштування та запуск скрапера
    TARGET_PAGE = "https://www.facebook.com/providentrealestateuz"
    OUTPUT_FILE = "facebook_posts.jsonl"
    MAX_POSTS = 15
    
    # Створення та запуск скрапера
    scraper = FacebookPropertyScraper(TARGET_PAGE, OUTPUT_FILE)
    
    # Запуск скрапінгу
    scraper.run(MAX_POSTS)