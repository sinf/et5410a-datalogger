
# ET5410A+ CSV+SQL data logger script

This script dumps voltage and current readings from East Tester ET5410A+ into a csv file (redirect stdout) and optionally into any database supported by SQL alchemy (sqlite, postgresql, etc...).  

I wanted to stream my measurements into a database but TestController won't do it. It can't append into a CSV file in real time and it will not even save anything at all if the program is stopped abruptly.  

# Link dump

[TestController](https://lygte-info.dk/project/TestControllerConfigDevice%20UK.html)  
A nice program that just works, but it is not open source and "user scripting" is limited to a poor custom bullshit language.  

[scippy](https://github.com/edmundsj/scippy.git)  
A small SCPI test  

