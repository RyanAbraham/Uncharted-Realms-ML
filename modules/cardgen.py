import numpy as np
import random
import json
from multiprocessing import Queue
from multiprocessing import Process
from multiprocessing import Value
from requests.exceptions import ConnectionError
from urllib.error import URLError
# Local libraries
import modules.namegen as namegen
import modules.imagegen as imagegen
import modules.mlnetwork as mlnetwork

csv_name = 'data/cards.csv'

HP_vals = [1]*3 + [2]*5 + [3]*5 + [4]*4 + [5]*3 + [6]*2 + [7]*2 + [8] + [9] + [10]
EFFs = ['Charge'] * 15 + ['Ward'] * 15
QUEUE_SIZE = 200

class CardGen:
    card_queue = Queue(QUEUE_SIZE)
    generating_cards = Value('i', False)
    current_id = 0
    @classmethod
    def generate_id(cls):
        cls.current_id += 1
        return cls.current_id

    # Generates a single new card
    def get_card(self):
        card_dict = {'NAME': [], 'POW': [], 'HP': [], 'IMG': [], 'EFF': []}
        names = []

        # Generate base card attributes, to be costed later

        # If we ran out of names, generate a new batch of 15
        if(names == []):
            try:
                names = namegen.generate_names()
            except ConnectionError:
                names = ['MISSINGNO.'] * 5
                print("Could not connect to name generation service")
        name = random.choice(names)
        names.remove(name)
        card_dict['NAME'].append(name)

        # HP is flat out a random int
        HP = random.choice(HP_vals)
        card_dict['HP'].append(HP)

        # Power is generated based on a gaussian distribution centred at the HP value
        POW = int(round(HP + np.random.normal(0, HP/2, 1)[0], 0))
        if(POW < 0):
            POW = 0
        card_dict['POW'].append(POW)

        try:
            img = imagegen.generate_image_url(name)
        except URLError:
            print("Could not connect to DeviantArt for image fetching")
            img = ""
        card_dict['IMG'].append(img)

        card_dict['EFF'].append(random.choice(EFFs))

        results = mlnetwork.predict_costs(card_dict)

        # Build the JSON for the response
        for index, card in results.iterrows():
            generated_card = {}
            generated_card['id'] = self.generate_id()
            generated_card['name'] = card['NAME']
            generated_card['pow'] = card['POW']
            generated_card['hp'] = card['HP']
            generated_card['clk'] = card['CLK']
            generated_card['eff'] = card['EFF']
            generated_card['img'] = card['IMG']

        return generated_card

    def get_cards(self, qty):
        cards = []
        for x in range(0, qty):
            while self.card_queue.empty():
                pass
            cards.append(self.card_queue.get())
        self.start_card_generation()
        return cards

    def start_card_generation(self):
        if(not self.generating_cards.value):
            gen_p = Process(target=self.generate_cards, args=(self.card_queue, self.generating_cards,))
            gen_p.start()
            self.generating_cards.value = True

    def generate_cards(self, card_queue, generating_cards):
        while not card_queue.full():
            card_queue.put(self.get_card())
            print("Card generated! Now " + str(card_queue.qsize()) + " in queue")
        print("Queue filled!")
        generating_cards.value = False
