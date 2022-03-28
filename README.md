# **LMS.NetMap**

### Description
**LMS.NetMap** - сетевой анализатор трафика с возможностью автоматического построения топологии сети. По факту, как и `Zenmap` это приложение является графической надстройкой над `nmap`, но задумка была сделать швейцарский нож для проведения пентеста.
Сейчас приложение умеет:
* сканировать сеть `nmap`-ом;
* парсить выдачу;
* парсить логи `nmap`-а;
* записывать полученный результат в базу (`SQLite`);
* Автоматический строить топологию сети (P.S. сейчас топология строиться только при наличии параметра `--traceroute`);
* Достраивать карту в ручном режиме;

На подходе:
* пассивное сканирование сети при помощи `scapy`(несколько широковещательных протоколов);
* предоставление краткой сводку о выделенном объекте на карте сети;
* сканирование с использование прокси;
* парсить выдаче `nmap`-а по максимому;

В планах:
* использование сканеров уязвимостей;
* детектирование `WAF` и `IPS`;
* техническая разведка(поиск сведений о домене, субдоменах, IP адресах);
* `dirbuster`;


### How to use
1. Переименовать `config.py.example` в `config.py`.
1. Указать в файле `config.py` сетевой интерфейс, который будем использовать, по желанию путь к папке, куда будут сохраняться логи сканирования.
1. Устанавливаем зависимости из `requirements.txt`. После следует удостоверится что у Вас установлен `nmap`, и что `scapy` коректно работает(просто запустить).
1. Запускаем `app.py` (желательно от `root`, потому что многие параметры `nmap`-а требуют рут-права).
1. Открываем в браузере `http://localhost:8050`, жмякаем `Active scan`. Вводим адрес цели(ей), выбираем параметры сканирования или вводим команду для скана руками.
1. Жмякаем `Scan` и ждем. После сканирования на веб странице должна отобразится топология просканировнной сети/узлов (только при наличии параметра `--traceroute`).

### Requirements
* `python 3`;
* в файле `requirements.txt`;
* `nmap`.
