# -*- coding: utf-8 -*-
# py -m pip install selenium undetected-chromedriver setuptools
import os
import glob
import re
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

def extract_urls(filepath):
    """
    Извлекает все ссылки на YouTube из файла.
    Использует регулярные выражения, поэтому работает даже с "кривыми" CSV из Takeout.
    """
    urls = []
    # Используем двойные кавычки для сырой строки, чтобы избежать конфликтов с экранированием
    pattern = re.compile(r"(https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|channel/|user/|c/|@|shorts/)[^\s\"',]+|youtu\.be/[^\s\"',]+))")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        found = pattern.findall(content)
        
        seen = set()
        for url in found:
            # Очищаем ссылку от лишних параметров плейлиста, чтобы скрипт переходил на чистое видео
            clean_url = url.rstrip('">').split('&list=')[0].split('&index=')[0].split('&t=')[0]
            if clean_url not in seen:
                seen.add(clean_url)
                urls.append(clean_url)
    return urls
  
def main():
    data_folder = "data"
    
    # Шаг 1: Проверка папки data
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
        print(f"Папка '{data_folder}' была автоматически создана.")
        print("Пожалуйста, поместите все ваши CSV-файлы из Google Takeout в эту папку и запустите скрипт заново.")
        return

    csv_files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not csv_files:
        print(f"В папке '{data_folder}' не найдено файлов .csv.")
        print("Положите туда файлы и перезапустите скрипт.")
        return

    print(f"Найдено CSV-файлов для обработки: {len(csv_files)}")
    tasks = []
    
    # Читаем все файлы заранее
    for filepath in csv_files:
        filename = os.path.basename(filepath)
        playlist_name = os.path.splitext(filename)[0] # Имя файла без .csv
        urls = extract_urls(filepath)
        
        if urls:
            tasks.append({
                "playlist_name": playlist_name,
                "urls": urls
            })
            print(f" - Файл '{filename}': найдено {len(urls)} ссылок")
            
    if not tasks:
        print("Во всех файлах не было найдено ни одной корректной ссылки YouTube.")
        return

    print("\nЗапускаем браузер Chrome (в режиме невидимки)...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    driver.maximize_window()
    # print("\nЗапускаем браузер Firefox...")
    # options = webdriver.FirefoxOptions()
    # options.set_preference("dom.webdriver.enabled", False)
    # options.set_preference('useAutomationExtension', False)
    # driver = webdriver.Firefox(options=options)
    # driver.maximize_window()
    
    try:
        # Шаг 2: Авторизация
        driver.get("https://www.youtube.com")
        print("\n============================================")
        print("ВНИМАНИЕ: Авторизуйтесь в новом аккаунте YouTube.")
        print("============================================")
        input("После успешного входа нажмите ENTER в этой консоли... ")
        
        wait = WebDriverWait(driver, 10)
        short_wait = WebDriverWait(driver, 3)
        
        # Шаг 3: Обход задач (файлов)
        for task in tasks:
            playlist_name = task["playlist_name"].strip()
            # Проверяем, является ли файл списком подписок
            is_subscriptions = playlist_name.lower() in ['subscriptions', 'подписки']
            
            print(f"\n=== Обработка: {playlist_name}.csv ===")
            if not is_subscriptions:
                print(f"-> Все видео из этого файла будут сохранены в плейлист: '{playlist_name}'")
                
            for index, url in enumerate(task["urls"], start=1):
                print(f"\n[{index}/{len(task['urls'])}] Открываем: {url}")
                driver.get(url)
                
                # Ждем прогрузки страницы/плеера
                time.sleep(random.uniform(4.0, 6.0))
                
                try:
                    is_video = "watch?v=" in url or "youtu.be" in url or "/shorts/" in url
                    
                    if is_video:
                        # --- ЛОГИКА ДЛЯ ВИДЕО (Плейлисты) ---
                        
                        # 1. Ищем кнопку Сохранить
                        try:
                            save_button = wait.until(EC.element_to_be_clickable((
                                By.XPATH, "//button[contains(@aria-label, 'Сохранить') or contains(@aria-label, 'Save') or contains(@title, 'Save') or contains(@title, 'Сохранить')]"
                            )))
                            save_button.click()
                        except TimeoutException:
                            # Кнопка может быть спрятана под тремя точками
                            menu_btn = wait.until(EC.element_to_be_clickable((
                                By.XPATH, "//button[@aria-label='More actions' or @aria-label='Другие действия']"
                            )))
                            menu_btn.click()
                            time.sleep(1)
                            save_button = wait.until(EC.element_to_be_clickable((
                                By.XPATH, "//ytd-menu-service-item-renderer[.//yt-formatted-string[contains(text(), 'Сохранить') or contains(text(), 'Save')]]"
                            )))
                            save_button.click()
                        
                        time.sleep(2.5) # Ждем открытия меню плейлистов
                        
                        # Особый случай для базового плейлиста
                        if playlist_name.lower() in ['watch later', 'смотреть позже']:
                            target_text_ru = "Смотреть позже"
                            target_text_en = "Watch later"
                        else:
                            target_text_ru = playlist_name
                            target_text_en = playlist_name
                            
                        # 2. Ищем плейлист в списке
                        try:
                            checkbox = short_wait.until(EC.presence_of_element_located((
                                By.XPATH, f"//tp-yt-paper-checkbox[.//yt-formatted-string[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя'), '{target_text_ru.lower()}') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя'), '{target_text_en.lower()}')]]"
                            )))
                            
                            is_checked = checkbox.get_attribute("aria-checked")
                            if is_checked == "true":
                                print(f"-> Уже в плейлисте '{playlist_name}'.")
                            else:
                                checkbox.click()
                                print(f"-> Добавлено в плейлист '{playlist_name}'!")
                                
                        except TimeoutException:
                            # 3. Если плейлиста нет, СОЗДАЕМ ЕГО
                            if playlist_name.lower() not in ['watch later', 'смотреть позже']:
                                print(f"-> Плейлист '{playlist_name}' не найден. Создаем новый...")
                                
                                # Клик "Создать новый плейлист"
                                create_new_btn = wait.until(EC.element_to_be_clickable((
                                    By.XPATH, "//ytd-add-to-playlist-create-renderer | //*[contains(text(), 'Создать новый плейлист') or contains(text(), 'Create new playlist')]"
                                )))
                                create_new_btn.click()
                                time.sleep(1.5)
                                
                                # Вводим название
                                input_field = wait.until(EC.presence_of_element_located((
                                    By.XPATH, "//input[@placeholder='Название' or @placeholder='Enter playlist name...'] | //ytd-playlist-add-to-option-renderer//input | //input[@id='input']"
                                )))
                                # Очищаем и пишем (используем Javascript, чтобы точно ввелось)
                                driver.execute_script("arguments[0].value = '';", input_field)
                                input_field.send_keys(playlist_name)
                                time.sleep(1)
                                
                                # Нажимаем Создать
                                create_submit = wait.until(EC.element_to_be_clickable((
                                    By.XPATH, "//*[@id='actions']//button[contains(@aria-label, 'Создать') or contains(@aria-label, 'Create') or span[contains(text(),'Создать')]] | //button[descendant::yt-formatted-string[contains(text(), 'Создать') or contains(text(), 'Create')]]"
                                )))
                                create_submit.click()
                                print(f"-> Плейлист '{playlist_name}' успешно создан и видео сохранено!")
                            else:
                                print("-> Ошибка: Базовый плейлист не найден. Возможно, интерфейс не загрузился.")
                                
                    else:
                        # --- ЛОГИКА ДЛЯ КАНАЛОВ (Подписки) ---
                        print("-> Обнаружен канал. Ищем кнопку 'Подписаться'...")
                        sub_button = wait.until(EC.element_to_be_clickable((
                            By.XPATH, "//div[@id='subscribe-button']//button[not(@disabled)]"
                        )))
                        aria_label = sub_button.get_attribute("aria-label") or ""
                        if "отменить" in aria_label.lower() or "unsubscribe" in aria_label.lower() or "вы подписаны" in aria_label.lower():
                            print("-> Вы уже подписаны на этот канал.")
                        else:
                            sub_button.click()
                            print("-> Успешно подписались на канал!")
                            
                except Exception as e:
                    print("-> [ОШИБКА] Не удалось обработать эту ссылку.")
                    # print(e) # Раскомментируйте для отладки
                    
                # Задержка перед следующей ссылкой
                delay = random.uniform(4.0, 7.0)
                time.sleep(delay)
                
            print(f"=== Файл {playlist_name}.csv обработан полностью! ===")
            
        print("\n>>> ВСЕ ФАЙЛЫ УСПЕШНО ОБРАБОТАНЫ! <<<")

    finally:
        print("Завершение работы браузера...")
        driver.quit()

if __name__ == "__main__":
    main()
