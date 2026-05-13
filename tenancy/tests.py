from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Tenancy, Payment, MaintenanceRequest
from properties.models import Property, Unit

User = get_user_model()

class ChatbotAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create landlord
        self.landlord = User.objects.create_user(username='landlord', email='owner@example.com', password='pass', user_type='landlord')
        # Create property and unit
        self.property = Property.objects.create(landlord=self.landlord, name='House 1', address='Somewhere', rent=500000)
        self.unit = Unit.objects.create(property=self.property, unit_number='A1', rent_amount=500000)
        # Create tenant and tenancy
        self.tenant = User.objects.create_user(username='tenant', email='tenant@example.com', password='pass', user_type='tenant')
        self.tenancy = Tenancy.objects.create(tenant=self.tenant, unit=self.unit, start_date=timezone.now().date())
        # Create a paid payment
        Payment.objects.create(tenancy=self.tenancy, amount=500000, date=timezone.now().date(), status='Paid', created_by=self.tenant)

    def test_chatbot_balance(self):
        # Login as tenant
        self.client.login(username='tenant', password='pass')
        url = reverse('tenancy:chatbot_api')
        response = self.client.post(url, data={'message': 'What is my balance?'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('reply', data)
        self.assertIn('Kodi', data['reply'] or data['reply'])

    def test_greeting_intent(self):
        self.client.login(username='tenant', password='pass')
        url = reverse('tenancy:chatbot_api')
        phrases = ['hi', 'hello', 'habari', 'habari gani', 'hey there', 'salaam']
        for p in phrases:
            resp = self.client.post(url, data={'message': p}, content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn('reply', data)
            self.assertTrue(any(x in data['reply'].lower() for x in ['habari', 'hello', 'ninaweza']))

    def test_help_intent(self):
        self.client.login(username='tenant', password='pass')
        url = reverse('tenancy:chatbot_api')
        phrases = ['help', 'i need help', 'how do i', 'nisaidie', 'what can i ask']
        for p in phrases:
            resp = self.client.post(url, data={'message': p}, content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn('reply', data)
            self.assertTrue(any(x in data['reply'].lower() for x in ['kodi', 'malipo', 'matengenezo', 'help']))

    def test_ask_price_intent(self):
        self.client.login(username='tenant', password='pass')
        url = reverse('tenancy:chatbot_api')
        phrases = ['how much is the rent', 'what is the price', 'bei ya kodi ni ngapi', 'rent amount?']
        for p in phrases:
            resp = self.client.post(url, data={'message': p}, content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn('reply', data)
            self.assertIn('tzs', data['reply'].lower())

    def test_ask_time_intent(self):
        self.client.login(username='tenant', password='pass')
        url = reverse('tenancy:chatbot_api')
        phrases = ['what time is it', 'tarehe ya leo', 'current time?', 'saa ni saa ngapi']
        for p in phrases:
            resp = self.client.post(url, data={'message': p}, content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn('reply', data)
            # Expect a timestamp-like response
            self.assertTrue(':' in data['reply'] or '-' in data['reply'])

    def test_goodbye_intent(self):
        self.client.login(username='tenant', password='pass')
        url = reverse('tenancy:chatbot_api')
        phrases = ['bye', 'goodbye', 'kwaheri', 'see you later']
        for p in phrases:
            resp = self.client.post(url, data={'message': p}, content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn('reply', data)
            self.assertTrue(any(x in data['reply'].lower() for x in ['kwaheri', 'bye']))

    def test_fallback_intent(self):
        self.client.login(username='tenant', password='pass')
        url = reverse('tenancy:chatbot_api')
        phrases = ['tell me a joke', 'sing a song', 'what is the weather like']
        for p in phrases:
            resp = self.client.post(url, data={'message': p}, content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn('reply', data)
            self.assertTrue('samahani' in data['reply'].lower() or 'unaweza kuuliza' in data['reply'].lower())

    def test_add_payment_page_loads(self):
        # Login and access add payment page for tenancy
        self.client.login(username='tenant', password='pass')
        url = reverse('tenancy:add_payment', args=[self.tenancy.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Choose Payment Method')
        # Ensure images are present
        self.assertContains(resp, 'mpesa.svg')
        self.assertContains(resp, 'halopesa.svg')
        self.assertContains(resp, 'crdb.svg')
        self.assertContains(resp, 'nmb.svg')