# -*- coding: utf-8 -*-
# py -m pip install selenium undetected-chromedriver setuptools
import os
import glob
import re
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def extract_maps_urls(filepath):
    """
    Извлекает ссылки на Google Карты из CSV-файла с помощью регулярных выражений.
    """
    urls = []
    # Используем тройные кавычки (r"""), чтобы безопасно искать любые символы внутри
    pattern = re.compile(r"""(https?://(?:[a-zA-Z0-9-]+\.)?google\.com/maps[^\s"',>]+|https?://goo\.gl/maps/[^\s"',>]+|https?://(?:[a-zA-Z0-9-]+\.)?googleusercontent\.com/maps[^\s"',>]+)""")
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        found = pattern.findall(content)
        
        seen = set()
        for url in found:
            # Очищаем от возможных артефактов в конце строки
            clean_url = url.rstrip('">')
            if clean_url not in seen:
                seen.add(clean_url)
                urls.append(clean_url)
    return urls

def main():
    data_folder = "Maps"
    
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
        print(f"Папка '{data_folder}' была автоматически создана.")
        print("Пожалуйста, поместите ваши CSV-файлы с сохраненными местами в эту папку и запустите скрипт заново.")
        return

    csv_files = glob.glob(os.path.join(data_folder, "*.csv"))
    if not csv_files:
        print(f"В папке '{data_folder}' не найдено файлов .csv.")
        print("Положите туда файлы из Takeout и перезапустите скрипт.")
        return

    print(f"Найдено CSV-файлов для обработки: {len(csv_files)}")
    tasks = []
    
    for filepath in csv_files:
        filename = os.path.basename(filepath)
        list_name = os.path.splitext(filename)[0]
        urls = extract_maps_urls(filepath)
        
        if urls:
            tasks.append({
                "list_name": list_name,
                "urls": urls
            })
            print(f" - Файл '{filename}': найдено {len(urls)} ссылок")
            
    if not tasks:
        print("Во всех файлах не было найдено ни одной корректной ссылки на Карты.")
        return

    print("\nЗапускаем браузер Chrome (в режиме невидимки)...")
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=148)
    driver.maximize_window()
    
    try:
        driver.get("https://accounts.google.com")
        print("\n============================================")
        print("ВНИМАНИЕ: Авторизуйтесь в новом аккаунте Google.")
        print("============================================")
        input("После успешного входа нажмите ENTER в этой консоли... ")
        
        wait = WebDriverWait(driver, 10)
        
        for task in tasks:
            list_name = task["list_name"].strip()
            print(f"\n=== Обработка списка: {list_name} ===")
            
            # Настройка умного поиска имени списка
            # В Takeout файлы часто на английском (Favorites), а интерфейс может быть на русском (Избранное)
            search_terms = [list_name]
            name_lower = list_name.lower()
            
            if name_lower in ['favorites', 'избранное']:
                search_terms.extend(['Избранное', 'Favorites'])
            elif name_lower in ['want to go', 'хочу посетить']:
                search_terms.extend(['Хочу посетить', 'Want to go'])
            elif name_lower in ['starred places', 'отмеченные места']:
                search_terms.extend(['Отмеченные места', 'Starred places'])
                
            for index, url in enumerate(task["urls"], start=1):
                print(f"\n[{index}/{len(task['urls'])}] Открываем место...")
                driver.get(url)
                
                time.sleep(random.uniform(3.5, 5.0))
                
                try:
                    # Ищем кнопку Сохранить (ожидаем присутствия, а не кликабельности)
                    save_button = wait.until(EC.presence_of_element_located((
                        By.XPATH, "//button[contains(@aria-label, 'Сохранить') or contains(@aria-label, 'Save') or @data-value='Сохранить']"
                    )))
                    
                    aria_label = save_button.get_attribute("aria-label") or ""
                    if "Сохранено" in aria_label or "Saved" in aria_label:
                        print("-> Место уже сохранено (возможно, в другом списке).")
                    
                    # ЖЕСТКИЙ КЛИК ЧЕРЕЗ JAVASCRIPT (игнорирует всплывающие окна)
                    driver.execute_script("arguments[0].click();", save_button)
                    
                    time.sleep(random.uniform(1.5, 2.5))
                    
                    # Генерируем XPath для поиска нужного списка по ключевым словам
                    xpath_conditions = " or ".join([f"contains(text(), '{term}')" for term in search_terms])
                    list_xpath = f"//div[{xpath_conditions}]"
                    
                    try:
                        target_list = wait.until(EC.presence_of_element_located((By.XPATH, list_xpath)))
                        # ЖЕСТКИЙ КЛИК по списку
                        driver.execute_script("arguments[0].click();", target_list)
                        print(f"-> Успешно добавлено в список '{list_name}'!")
                    except TimeoutException:
                        print(f"-> [ПРЕДУПРЕЖДЕНИЕ] Список '{list_name}' не найден в меню.")
                        print("   Место сохранено, но вам нужно создать этот список в Картах вручную, если это кастомный список.")
                        # Закрываем меню кликом в сторону или esc, чтобы продолжить (опционально)
                        
                except Exception as e:
                    print("-> [ОШИБКА] Не удалось сохранить это место.")
                    print(f"   Детали: {type(e).__name__}")
                    
                delay = random.uniform(4.0, 7.0)
                time.sleep(delay)
                
            print(f"=== Список {list_name} обработан полностью! ===")
            
        print("\n>>> ВСЕ МЕСТА УСПЕШНО ПЕРЕНЕСЕНЫ! <<<")

    finally:
        print("Завершение работы браузера...")
        driver.quit()

if __name__ == "__main__":
    main()
