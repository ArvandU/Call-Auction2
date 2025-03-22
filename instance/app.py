from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
CORS(app)

# Configure logging
if not app.debug:
    file_handler = RotatingFileHandler('auction.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Auction startup')

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'auction.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
db = SQLAlchemy(app)

# Ensure instance folder and file exist
os.makedirs(os.path.dirname(db_path), exist_ok=True)
if not os.path.isfile(db_path):
    open(db_path, 'a').close()

# ---------------------------
# Database Models
# ---------------------------
class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.String(10), unique=True, nullable=False)  # e.g., "b1", "s2"
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # bidder1, bidder2, seller1, seller2
    initial_money = db.Column(db.Float, default=0)
    water = db.Column(db.Float, default=0)
    marginal_value_first = db.Column(db.Float, default=0)
    marginal_value_second = db.Column(db.Float, default=0)
    tokens = db.Column(db.Float, default=0)

class ParticipantResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.String(10), nullable=False)
    answer1 = db.Column(db.Text, nullable=True)
    answer2 = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ParticipantBid(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'bid' or 'ask'
    round_number = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AuctionRound(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.Integer, nullable=False)
    uniform_price = db.Column(db.Float, nullable=False)
    total_quantity = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# New table to store each participant's result per round.
class ParticipantRoundResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.Integer, nullable=False)
    participant_id = db.Column(db.String(10), nullable=False)
    executed_quantity = db.Column(db.Integer, nullable=False)
    profit = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    app.logger.info('Database initialized successfully')

# ---------------------------
# Global Round Tracker
# ---------------------------
current_round = 1
TOTAL_ROUNDS = 8

# ----------------------------------------------------------
# Process Round: Compute Clearing Based on Submitted Orders
#
# Matching algorithm:
#  1. Separate buyer (bid) and seller (ask) orders for the current round,
#     sorting buyers descending by price and sellers ascending.
#  2. While the highest bid is at least the lowest ask, clear trade for the
#     minimum quantity and record that trade.
#  3. Uniform price is the average of the last matched bid and ask prices.
#
# Then, for each participant, executed quantity and profit are computed:
#   - Buyers:
#       • If only one cleared order, profit = (marginal_value_first - uniform_price) × quantity.
#       • If multiple, first order uses marginal_value_first and the rest marginal_value_second.
#   - Sellers:
#       • If only one cleared order, profit = (uniform_price - marginal_value_second) × quantity.
#       • If multiple, first order uses marginal_value_second and the rest marginal_value_first.
#
# Each participant's result is then stored in ParticipantRoundResult.
# ----------------------------------------------------------
def process_bid_round():
    global current_round
    # Save the round number being processed
    round_number_processed = current_round

    # Fetch all orders for the current round
    orders = ParticipantBid.query.filter_by(round_number=round_number_processed).all()
    
    # Separate orders into buyer and seller lists (copies of order data)
    buyer_orders = []
    seller_orders = []
    for order in orders:
        if order.type == 'bid':
            buyer_orders.append({'participant_id': order.participant_id, 'price': order.price, 'quantity': order.quantity})
        elif order.type == 'ask':
            seller_orders.append({'participant_id': order.participant_id, 'price': order.price, 'quantity': order.quantity})
    
    # Sort buyer orders (highest price first) and seller orders (lowest price first)
    buyer_orders.sort(key=lambda o: (-o['price'], o['quantity']))
    seller_orders.sort(key=lambda o: (o['price'], o['quantity']))
    
    # Matching process: record executed trades for each participant
    buyer_trade_info = {}   # participant_id -> list of traded quantities
    seller_trade_info = {}
    i = 0
    j = 0
    last_bid_price = None
    last_ask_price = None
    total_traded = 0
    while i < len(buyer_orders) and j < len(seller_orders):
        # Stop if highest bid is less than lowest ask
        if buyer_orders[i]['price'] < seller_orders[j]['price']:
            break
        trade_qty = min(buyer_orders[i]['quantity'], seller_orders[j]['quantity'])
        total_traded += trade_qty
        last_bid_price = buyer_orders[i]['price']
        last_ask_price = seller_orders[j]['price']
        # Record trade for buyer
        pid_b = buyer_orders[i]['participant_id']
        buyer_trade_info.setdefault(pid_b, []).append(trade_qty)
        # Record trade for seller
        pid_s = seller_orders[j]['participant_id']
        seller_trade_info.setdefault(pid_s, []).append(trade_qty)
        buyer_orders[i]['quantity'] -= trade_qty
        seller_orders[j]['quantity'] -= trade_qty
        if buyer_orders[i]['quantity'] == 0:
            i += 1
        if seller_orders[j]['quantity'] == 0:
            j += 1
    
    if total_traded > 0:
        uniform_price = (last_bid_price + last_ask_price) / 2
    else:
        uniform_price = 0

    # Compute executed quantity and profit for each participant
    participant_results = {}
    
    # Process buyers (roles: bidder1, bidder2)
    buyers = Participant.query.filter(Participant.role.in_(['bidder1', 'bidder2'])).all()
    for buyer in buyers:
        trades = buyer_trade_info.get(buyer.participant_id, [])
        executed_quantity = sum(trades)
        if trades:
            if len(trades) == 1:
                profit = (buyer.marginal_value_first - uniform_price) * trades[0]
            else:
                profit = (buyer.marginal_value_first - uniform_price) * trades[0] \
                         + (buyer.marginal_value_second - uniform_price) * sum(trades[1:])
        else:
            profit = 0
        participant_results[buyer.participant_id] = {'executed_quantity': executed_quantity, 'profit': profit}
    
    # Process sellers (roles: seller1, seller2)
    sellers = Participant.query.filter(Participant.role.in_(['seller1', 'seller2'])).all()
    for seller in sellers:
        trades = seller_trade_info.get(seller.participant_id, [])
        executed_quantity = sum(trades)
        if trades:
            if len(trades) == 1:
                profit = (uniform_price - seller.marginal_value_second) * trades[0]
            else:
                profit = (uniform_price - seller.marginal_value_second) * trades[0] \
                         + (uniform_price - seller.marginal_value_first) * sum(trades[1:])
        else:
            profit = 0
        participant_results[seller.participant_id] = {'executed_quantity': executed_quantity, 'profit': profit}
    
    # Update tokens for each participant (accumulate profit)
    for pid, res in participant_results.items():
        participant = Participant.query.filter_by(participant_id=pid).first()
        if participant:
            participant.tokens += res['profit']
    db.session.commit()
    
    # Save round result (round-level)
    round_result = AuctionRound(
        round_number=round_number_processed,
        uniform_price=uniform_price,
        total_quantity=total_traded
    )
    db.session.add(round_result)
    
    # Save participant results for this round in the new table
    for pid, res in participant_results.items():
        prr = ParticipantRoundResult(
            round_number=round_number_processed,
            participant_id=pid,
            executed_quantity=res['executed_quantity'],
            profit=res['profit']
        )
        db.session.add(prr)
    
    db.session.commit()
    
    result = {
        'uniform_price': uniform_price,
        'total_quantity': total_traded,
        'participant_results': participant_results,
        'round_number': round_number_processed
    }
    current_round += 1
    return result

# ----------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    first_name = data.get('firstName')
    last_name = data.get('lastName')
    if not first_name or not last_name:
        return jsonify({'error': 'Missing registration fields'}), 400
    existing = Participant.query.all()
    if len(existing) >= 4:
        return jsonify({'error': 'Maximum number of participants reached.'}), 400
    roles = {
        'bidder1': {
            'participant_id': 'b1',
            'initial_money': 100,
            'water': 0,
            'marginal_value_first': 8,
            'marginal_value_second': 6
        },
        'bidder2': {
            'participant_id': 'b2',
            'initial_money': 120,
            'water': 0,
            'marginal_value_first': 10,
            'marginal_value_second': 8
        },
        'seller1': {
            'participant_id': 's1',
            'initial_money': 0,
            'water': 14,
            'marginal_value_first': 6,
            'marginal_value_second': 4
        },
        'seller2': {
            'participant_id': 's2',
            'initial_money': 0,
            'water': 16,
            'marginal_value_first': 8,
            'marginal_value_second': 6
        }
    }
    assigned_roles = {p.role for p in existing}
    available = {role: info for role, info in roles.items() if role not in assigned_roles}
    if not available:
        return jsonify({'error': 'No available roles.'}), 400
    chosen_role = list(available.keys())[0]
    role_data = available[chosen_role]
    new_participant = Participant(
        participant_id=role_data['participant_id'],
        first_name=first_name,
        last_name=last_name,
        role=chosen_role,
        initial_money=role_data['initial_money'],
        water=role_data['water'],
        marginal_value_first=role_data['marginal_value_first'],
        marginal_value_second=role_data['marginal_value_second'],
        tokens=0
    )
    db.session.add(new_participant)
    db.session.commit()
    return jsonify({'message': 'Registration successful!', 'participantId': new_participant.participant_id}), 200

@app.route('/submit_description', methods=['POST'])
def submit_description():
    data = request.json
    participant_id = data.get('participantId')
    answer1 = data.get('answer1')
    answer2 = data.get('answer2')
    if not participant_id:
        return jsonify({'error': 'Participant ID is required'}), 400
    new_response = ParticipantResponse(
        participant_id=participant_id,
        answer1=answer1,
        answer2=answer2
    )
    db.session.add(new_response)
    db.session.commit()
    return jsonify({'message': 'Description submitted successfully!'}), 200

@app.route('/bid_submit', methods=['POST'])
def bid_submit():
    global current_round
    if current_round > TOTAL_ROUNDS:
        return jsonify({'message': 'Auction completed. No further rounds are allowed.', 'round_number': current_round - 1}), 200

    data = request.json
    participant_id = data.get('participantId')
    bids = data.get('bids', [])
    if not participant_id or not bids:
        return jsonify({'error': 'Participant ID and bids are required'}), 400

    existing_bid = ParticipantBid.query.filter_by(round_number=current_round, participant_id=participant_id).first()
    if existing_bid:
        return jsonify({'message': 'You have already submitted bids for the current round. Please wait for the round results.'}), 200

    try:
        for bid in bids:
            if not all(k in bid for k in ['price', 'quantity', 'type']):
                raise ValueError("Missing fields in bid submission")
            new_bid = ParticipantBid(
                participant_id=participant_id,
                price=bid['price'],
                quantity=bid['quantity'],
                type=bid['type'],
                round_number=current_round
            )
            db.session.add(new_bid)
        db.session.commit()

        all_orders = ParticipantBid.query.filter_by(round_number=current_round).all()
        distinct_participants = set(o.participant_id for o in all_orders)
        if len(distinct_participants) < 4:
            return jsonify({
                'message': 'Waiting for other participants to submit bids for this round.',
                'round_number': current_round
            }), 200
        else:
            round_info = process_bid_round()
            participant_result = round_info['participant_results'].get(participant_id, {'executed_quantity': 0, 'profit': 0})
            if round_info['round_number'] == TOTAL_ROUNDS:
                response = {
                    'round_info': {
                        'uniform_price': round_info['uniform_price'],
                        'total_quantity': round_info['total_quantity'],
                        'round_number': round_info['round_number']
                    },
                    'participant_result': participant_result,
                    'message': 'Auction completed. This was the final round.'
                }
            else:
                response = {
                    'round_info': {
                        'uniform_price': round_info['uniform_price'],
                        'total_quantity': round_info['total_quantity'],
                        'round_number': round_info['round_number']
                    },
                    'participant_result': participant_result,
                    'message': 'Round processed successfully.'
                }
            return jsonify(response), 200
    except Exception as e:
        db.session.rollback()
        print("Error in bid_submit:", e)
        return jsonify({'error': str(e)}), 400

@app.route('/round_result', methods=['GET'])
def round_result():
    participant_id = request.args.get('participantId')
    round_number = request.args.get('roundNumber')
    if not participant_id or not round_number:
        return jsonify({'error': 'Missing participantId or roundNumber'}), 400
    round_number = int(round_number)
    auction_round = AuctionRound.query.filter_by(round_number=round_number).first()
    if not auction_round:
        return jsonify({}), 200
    orders = ParticipantBid.query.filter_by(round_number=round_number, participant_id=participant_id).all()
    uniform_price = auction_round.uniform_price
    executed_quantity = 0
    profit = 0
    participant = Participant.query.filter_by(participant_id=participant_id).first()
    if not participant:
        return jsonify({'error': 'Participant not found'}), 400
    cleared_orders = []
    for order in orders:
        if order.type == 'bid' and order.price >= uniform_price:
            cleared_orders.append(order)
        elif order.type == 'ask' and order.price <= uniform_price:
            cleared_orders.append(order)
    if participant.role in ['bidder1', 'bidder2']:
        cleared_sorted = sorted(cleared_orders, key=lambda o: (-o.price, o.id))
        allocated = 10
        remaining = allocated
        for idx, order in enumerate(cleared_sorted):
            if remaining <= 0:
                break
            qty = min(order.quantity, remaining)
            executed_quantity += qty
            margin = participant.marginal_value_first if idx == 0 else participant.marginal_value_second
            profit += (margin - order.price) * qty
            remaining -= qty
    else:
        cleared_sorted = sorted(cleared_orders, key=lambda o: (o.price, o.id))
        for idx, order in enumerate(cleared_sorted):
            executed_quantity += order.quantity
            margin = participant.marginal_value_second if idx == 0 else participant.marginal_value_first
            profit += (uniform_price - margin) * order.quantity
    result = {
        'round_number': round_number,
        'uniform_price': uniform_price,
        'total_quantity': auction_round.total_quantity,
        'executed_quantity': executed_quantity,
        'profit': profit
    }
    return jsonify({'round_info': result}), 200

@app.route('/final_tokens', methods=['GET'])
def final_tokens():
    participant_id = request.args.get('participantId')
    participant = Participant.query.filter_by(participant_id=participant_id).first()
    if not participant:
        return jsonify({'error': 'Participant not found'}), 404
    return jsonify({
        'participantId': participant.participant_id,
        'total_tokens': participant.tokens
    }), 200

@app.route('/participant_info', methods=['GET'])
def participant_info():
    participant_id = request.args.get('participantId')
    participant = Participant.query.filter_by(participant_id=participant_id).first()
    if not participant:
        return jsonify({'error': 'Participant not found'}), 404
    info = {
        'initial_money': participant.initial_money,
        'water': participant.water,
        'marginal_value_first': participant.marginal_value_first,
        'marginal_value_second': participant.marginal_value_second,
        'profit_function': ("For buyers: Profit = (Assigned Marginal Value – Order Price) × Executed Quantity. "
                             "For sellers: Profit = (Uniform Price – Assigned Marginal Value) × Executed Quantity."),
        'auction_rule': "The auction uses a call auction mechanism with a uniform price."
    }
    return jsonify(info), 200

# Update the main block for production
if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()
            app.logger.info('Database initialized successfully')
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    except Exception as e:
        app.logger.error(f'Error starting application: {str(e)}')
        raise
