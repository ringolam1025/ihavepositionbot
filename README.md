# I Have Position Bot
IhavePositionBot (This bot) is using python to develop which is developed for more easy to calculate what is the save position for the users. 

# Main Function
Send the bot message like below format, the bot can calculate the profit and loss for your trade.  
```
ygg
long 2.495
stop 2.1
tp 2.9 3.4
1%
```
| String      | Description                          |
| ----------- | ------------------------------------ |
| ygg         | coin name                            |
| long 2.495  | order type and entry price           |
| stop 2.1    | stop loss                            |
| tp 2.9 3.4  | tp price(s)                          |
| 1%          | Acceptable percent loss of capital   |


The entry price in range. 
```
anc
long zone 2.8 - 3
stop 2.6
tp 4 6
0.5%
````
| String      | Description                          |
| ----------- | ------------------------------------ |
| ygg         | coin name                            |
| long 2.495  | order type and entry price           |
| stop 2.1    | stop loss                            |
| tp 2.9 3.4  | tp price(s)                          |
| 1%          | Acceptable percent loss of capital   |

# Error handling
The bot will send an email to administrator when throw exception
![Vars config in Heroku](/asset/error_email.png)

# Running on local
Create `.env`
```
NAME=
TOKEN=
PORT=5000
LOG_FILE_PATH=./logs/ihaveposition.log
DBLINK=
MODE=DEV
HEROKULINK=
FROMADDRESS=
TOADDRESS=
GMAILAPPPW=
SMTP=smtp.gmail.com
```

# Running on Cloud
The bot is now depolyed to Heroku. Before upload to Heroku you need to setting below varable. 
> Reminder to set `MODE = PROD`

![Vars config in Heroku](/asset/ihaveposition_heroku.png)


# Future Functions
- [ ] User custom setting (captial, acceptable loss, etc)
- [ ] Connect to exchange for copy trading