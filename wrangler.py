from flask import Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
import models
from models import *
import os
from sqlalchemy import exc
import logging

def setup_logger():
    log_dir = os.path.dirname(os.path.abspath(__file__)) + "/logs/"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(filename=log_dir + "hashtop-wrangler-svc.log", filemode='w', level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(name)s %(message)s')
    logger = logging.getLogger(__name__)

    return logger

logger = setup_logger()

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = models.conn_str
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# not using flask sqlalchemy for models so they can be used without a flask app
db = SQLAlchemy(metadata=models.metadata)
db.init_app(app)


@app.route('/user', methods=['POST', 'PUT'])
@app.route('/user/<wallet_addr>', methods=['GET', 'DELETE'])
def user(wallet_addr = None):
    # insert a new user into the db
    if request.method == 'POST':
        new_user = User(fname=request.args.get('fname'),
                        lname=request.args.get('lname'),
                        wallet_addr=request.args.get('wallet_addr'),
                        )
        db.session.add(new_user)
        try:
            db.session.commit()
            return Response(response="New user inserted", status=200, mimetype='text/plain')
        except exc.SQLAlchemyError as e:
            response = Response(response=e, status=500, mimetype='text/plain')
            logger.error(e)
            return response

    # update a users info but not their stats (name, etc)
    elif request.method == 'PUT':
        address = request.args.get('wallet_addr')
        if address:
            update_user = db.session.query(User).filter_by(wallet_addr=address)
            update_user.update(request.args)
            try:
                db.session.commit()
                return Response(response="User updated", status=200, mimetype='text/plain')
            except exc.SQLAlchemyError as e:
                response = Response(response=e, status=500, mimetype='text/plain')
                logger.error(e)
                return response
        else:
            return Response(status=400)

    # get all users stats
    elif request.method == 'GET':
        user_stat = db.session.query(UserStat).filter_by(wallet_addr=wallet_addr).first()
        return jsonify(user_stat.as_dict())

    # delete a user
    elif request.method == 'DELETE':
        delete_user = db.session.query(User).filter_by(wallet_addr=wallet_addr).first()
        db.session.delete(delete_user)
        try:
            db.session.commit()
            return Response(response=wallet_addr+" deleted", status=200, mimetype='text/plain')
        except exc.SQLAlchemyError as e:
            response = Response(response=e, status=500, mimetype='text/plain')
            logger.error(e)
            return response

@app.route('/miner', methods=['POST'])
@app.route('/miner/<miner_id>', methods=['GET', 'PUT'])
def miner_stats(miner_id=None):
    # insert a new miner into the db
    if request.method == 'POST':
        address = request.args.get('wallet_addr')
        user = db.session.query(User).filter_by(wallet_addr=address).first()
        new_miner = Miner(wallet_addr=address,
                          user=user)
        db.session.add(new_miner)
        try:
            db.session.commit()
            return Response(response="New miner inserted", status=200, mimetype='text/plain')
        except exc.SQLAlchemyError as e:
            response = Response(response=e, status=500, mimetype='text/plain')
            logger.error(e)
            return response

    # get the current health of the miners gpus
    # TODO: add query param to limit timeframe
    elif request.method == 'GET':
        miner = db.session.query(Miner).filter_by(id=miner_id).first()
        gpus = db.session.query(Gpu).filter_by(miner=miner)
        miner_dict = miner.as_dict()
        gpus = [g.as_dict() for g in gpus]
        return jsonify({
            'miner': miner_dict,
            'gpus': gpus
        })

    # update the health of the gpus associated with a miner
    elif request.method == 'PUT':
        gpus = request.json
        bulk = []
        for g in gpus:

            miner = db.session.query(Miner).filter_by(id=miner_id).first()
            gpu = db.session.query(Gpu).filter_by(miner=miner, gpu_no=g['gpu_no']).first()

            if not gpu:
                gpu = Gpu(#miner_id=miner_id,
                          miner=miner,
                          gpu_no=g['gpu_no'])

            health = Health(#miner_id=miner_id,
                            #gpu_no=g['gpu_no'],
                            temperature=g['temperature'],
                            power=g['power'],
                            hashrate=g['hashrate'])
            # update the miners list of gpus
            miner.gpus.append(gpu)
            # update the health of the gpu
            gpu.healths.append(health)

            db.session.add(miner)
            db.session.add(gpu)
            db.session.add(health)

        try:
            db.session.commit()
            return Response(response="Health updated", status=200, mimetype='text/plain')
        except exc.SQLAlchemyError as e:
            response = Response(response=e, status=500, mimetype='text/plain')
            logger.error(e)
            return response


if __name__ == '__main__':
    app.run(threaded=True, port=5000)
