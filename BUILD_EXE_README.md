# 🚀 Как да създадете EXE файл за OptiRoute

## Метод 1: Автоматично създаване (Препоръчан)

### Стъпка 1: Инсталиране на PyInstaller
```bash
pip install pyinstaller
```

### Стъпка 2: Създаване на EXE файл
```bash
pyinstaller --onefile --console --name OptiRoute main.py
```

### Стъпка 3: Намиране на EXE файла
EXE файлът ще се създаде в папката `dist/` с име `OptiRoute.exe`

## Метод 2: Използване на batch файл

### Стъпка 1: Стартиране на batch файла
```bash
.\build_exe_simple.bat
```

### Стъпка 2: Изчакване на създаването
Процесът може да отнеме 2-5 минути.

## Метод 3: Подробна конфигурация

### Стъпка 1: Създаване с spec файл
```bash
pyinstaller optiroute_simple.spec
```

### Стъпка 2: Проверка на резултата
```bash
dir dist\OptiRoute.exe
```

## ⚠️ Важни забележки

### 1. Размер на EXE файла
- EXE файлът ще бъде голям (50-100 MB)
- Това е нормално, защото включва Python интерпретатора

### 2. Необходими файлове
Преди да стартирате EXE файла, се уверете че имате:
- `data/input.xlsx` - входни данни
- `config.py` - конфигурация (ако е нужно)

### 3. Първо стартиране
При първото стартиране EXE файлът може да:
- Отнеме повече време за зареждане
- Създаде необходимите папки автоматично

## 🛠️ Решаване на проблеми

### Проблем: "ModuleNotFoundError"
**Решение**: Добавете липсващия модул в spec файла:
```python
hiddenimports=['липсващ_модул']
```

### Проблем: "FileNotFoundError"
**Решение**: Уверете се че всички необходими файлове са в правилните папки.

### Проблем: Голям размер на EXE
**Решение**: Използвайте `--onedir` вместо `--onefile`:
```bash
pyinstaller --onedir --console --name OptiRoute main.py
```

## 📁 Структура след създаване

```
OptiRoute_Final/
├── dist/
│   └── OptiRoute.exe          # Вашият EXE файл
├── build/                      # Временни файлове
├── main.py                     # Основен файл
├── config.py                   # Конфигурация
└── data/
    └── input.xlsx              # Входни данни
```

## 🚀 Стартиране на EXE файла

### От командния ред:
```bash
dist\OptiRoute.exe
```

### От Windows Explorer:
Двойно кликване върху `OptiRoute.exe` в папката `dist/`

## 📋 Проверка на функционалността

След създаването на EXE файла, тествайте:

1. **Стартиране**: `dist\OptiRoute.exe`
2. **Обработка на данни**: Поставете `input.xlsx` в папката `data/`
3. **Генериране на резултати**: Проверете папката `output/`

## 🔧 Допълнителни опции

### Създаване на EXE без конзола:
```bash
pyinstaller --onefile --windowed --name OptiRoute main.py
```

### Създаване с икона:
```bash
pyinstaller --onefile --console --icon=icon.ico --name OptiRoute main.py
```

### Оптимизация за размер:
```bash
pyinstaller --onefile --console --strip --name OptiRoute main.py
```

## ✅ Успешно създаване

Когато EXE файлът е създаден успешно, ще видите:
- ✅ EXE файл в папката `dist/`
- ✅ Размер около 50-100 MB
- ✅ Възможност за стартиране от командния ред

**Готово! Вашата програма сега може да се стартира като EXE файл! 🎉** 