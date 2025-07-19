# fit_acquisition/test.py

from fit_acquisition.class_names import (
    class_names,
)  # ✅ importa l'istanza, non il modulo

print("▶️  Accesso a costanti predefinite:")

print("PACKETCAPTURE =", class_names.PACKETCAPTURE)
print("REPORT        =", class_names.REPORT)

print("\n▶️  Registrazione dinamica di un nuovo task:")
class_names.register("WHATSAPP", "TaskWhatsApp")
print("WHATSAPP      =", class_names.WHATSAPP)

print("\n▶️  Uso in una lista di post-task:")

(
    ZIP_AND_REMOVE_FOLDER,
    SAVE_CASE_INFO,
    HASH,
    REPORT,
    TIMESTAMP,
    PEC_AND_DOWNLOAD_EML,
) = (
    class_names.ZIP_AND_REMOVE_FOLDER,
    class_names.SAVE_CASE_INFO,
    class_names.HASH,
    class_names.REPORT,
    class_names.TIMESTAMP,
    class_names.PEC_AND_DOWNLOAD_EML,
)

post_tasks = (
    ZIP_AND_REMOVE_FOLDER,
    SAVE_CASE_INFO,
    HASH,
    REPORT,
    TIMESTAMP,
    PEC_AND_DOWNLOAD_EML,
)

print("POST TASKS:")
for task in post_tasks:
    print("  -", task)

print("\n▶️  Elenco completo delle costanti registrate:")
for name, value in class_names.list_all().items():
    print(f"{name} = {value}")
