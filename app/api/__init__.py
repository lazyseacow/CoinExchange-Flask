from flask import Blueprint

api = Blueprint('api', __name__)

from . import passport, market, wallet, admin, transaction
