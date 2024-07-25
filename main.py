from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
import models
import yfinance as yf
from database import SessionLocal,engine
from sqlalchemy.orm import Session
from pydantic import BaseModel #pydantic structures http request ,it is builtin in fastapi
from models import Stock
app = FastAPI()

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

class StockRequest(BaseModel):
      symbol: str
def get_db():
      try:
            db = SessionLocal()
            yield db
      finally:
            db.close()
@app.get("/")
def dashboard(request: Request,forward_pe= None,dividend_yield =None,ma50=None,ma200=None, db: Session= Depends(get_db)):
    #displays the dashboard/homepage

    stocks =db.query(Stock)
    if forward_pe :
         stocks=stocks.filter(Stock.forward_pe < forward_pe)
    if dividend_yield:
         stocks =stocks.filter(Stock.dividend_yield < dividend_yield)
    if ma50:
        stocks =stocks.filter(Stock.price > Stock.ma50)
    if ma200:
        stocks =stocks.filter(Stock.price > Stock.ma200)
    return templates.TemplateResponse("dashboard.html",{
        "request": request,
        "stocks" : stocks,
        "dividend_yield" :dividend_yield,
        "forward_pe" :forward_pe,
        "ma50" : ma50,
        "ma200" : ma200
        
    })
def fetch_stock_data(id: int): #this id integer is the reference to primary key in database
    db = SessionLocal()
    stock = db.query(Stock).filter(Stock.id == id).first()
    yahoo_data = yf.Ticker(stock.symbol)
    

    stock.ma200 = yahoo_data.info['twoHundredDayAverage']
    if yahoo_data.info['fiftyDayAverage'] is not None:
        stock.ma50 = yahoo_data.info['fiftyDayAverage']
    stock.price = yahoo_data.info['previousClose']
    stock.forward_pe = yahoo_data.info['forwardPE']
    stock.forward_eps = yahoo_data.info['forwardEps']
    try:
        dividend_yield = yahoo_data.info['dividendYield']
        stock.dividend_yield = dividend_yield * 100
    except KeyError:
        stock.dividend_yield = None
    db.add(stock)
    db.commit()
@app.post("/stock")
async def create_stock(stock_request: StockRequest,background_tasks :BackgroundTasks, db: Session= Depends(get_db)): #stock_request: StockRequest   variable: type of variable
    # create a stock and store  in database 

    stock=Stock()
    stock.symbol = stock_request.symbol
    db.add(stock)
    db.commit()

    background_tasks.add_task(fetch_stock_data, stock.id)
    return {
        "code": "success",
        "message":"stock created"
        }