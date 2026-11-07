#!/usr/bin/env python3
"""Whether a Fankha copy has marginal notes, from its own text (fahares item 87, step 14.75).

judge(text) gives «notes» on strong evidence of notes («دارای حواشی با نشان «منه»», «محشی», «در حاشیه تصحیح شده»),
«not_notes» when every use of the word is the place of the text (a work copied in the margins of another book,
«1ص (87ر حاشیه)»), the layout of lines or decoration and binding, and «unclear» otherwise; «none» when the word is absent.
The flag was changed only where this and a reading of the copy agreed (reports/fankha_v2_db_review8/marginal_notes_step14_75).
"""
W = r'(?:حاشیه|حاشيه|حواشی|حواشي)'
NOTE = re.compile('|'.join([
    r'محشی|محشا|محشّی|تعلیقات|تعلیقه|هامش|حاشیه[\s‌]*نویسی|حاشیه[\s‌]*نگاری',
    r'دارای\s+(?:\S+\s+){0,2}' + W + r'(?!\s*(?:مذهب|زرین|طلا|زر|مجدول|جدول|تذهیب|رنگین))',
    W + r'\s+(?:\S+\s+){0,2}(?:با|به)\s+(?:نشان|نشانه|امضای|امضا|رمز|علامت)',
    W + r'\s+(?:از|به\s+خط)\s+(?!\S*\s*(?:زر|طلا))',
    r'(?:ترجمه|توضیح|شرح)\S*\s+(?:\S+\s+){0,2}در\s+' + W,
    W + r'\s+(?:دارد|دارند|بسیار|فراوان|زیاد|کوتاه|مختصر|مفصل|متعدد|اندک|پراکنده|عربی|فارسی)',
    r'در\s+' + W + r'(?:\s+\S+){0,6}?\s+(?:تصحیح|نوشته|آمده|افزوده|قید|ثبت|یادداشت|توضیح|اضافه|نگاشته\s+شده\s+(?:است\s+)?که|ذکر|دیده)',
]))
# «4ص (60 حاشیه-63حاشیه)», «(حاشیه 1-29)», «31 نیم سطر در حواشی», a binding or illumination clause
NOT = re.compile('|'.join([
    r'\([^)]*' + W + r'[^)]*\d[^)]*\)|\([^)]*\d[^)]*' + W + r'[^)]*\)',
    r'سطر\s+(?:\S+\s+){0,2}در\s+' + W,
    r'(?:جلد|ترنج|سرترنج|سرلوح|کتیبه)[^؛،]{0,40}?' + W,
    W + r'\s+(?:مذهب|زرین|طلا|زر|مجدول|جدول|تذهیب|رنگین|مرصع)',
    r'در\s+' + W + r'(?:\s+\S+){0,3}?\s+(?:تذهیب|دایره|ترنج|گل|مذهب)',
    r'در\s+' + W + r'\s+به\s+طریق\s+مورب|در\s+' + W + r'\s+(?:نوشته|نگاشته)\s+شده(?:\s*[،؛]|\s*$)',
]))
WORD = re.compile(W + r'|محشی|محشا|تعلیق|هامش')

def judge(text):
    body = text.split('\n', 1)[1] if '\n' in text else text
    body = re.sub(r'<!--\s*page:\s*\d+\s*-->', ' ', body)
    if NOTE.search(body):
        return 'notes'
    uses = len(WORD.findall(body))
    if not uses:
        return 'none'
    rest = NOT.sub(' ', body)
    return 'not_notes' if not WORD.search(rest) else 'unclear'
