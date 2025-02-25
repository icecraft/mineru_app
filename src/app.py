# Copyright (c) Opendatalab. All rights reserved.

import base64
import os
import re
import uuid
import requests
from pathlib import Path
import time 
import zipfile
import string
import random
import fitz
import json

import gradio as gr
import pymupdf
from gradio_pdf import PDF
from importlib.resources import files
from dotenv import load_dotenv

load_dotenv()


class BlockType:
    Image = 'image'
    ImageBody = 'image_body'
    ImageCaption = 'image_caption'
    ImageFootnote = 'image_footnote'
    Table = 'table'
    TableBody = 'table_body'
    TableCaption = 'table_caption'
    TableFootnote = 'table_footnote'
    Text = 'text'
    Title = 'title'
    InterlineEquation = 'interline_equation'
    Footnote = 'footnote'
    Discarded = 'discarded'
    List = 'list'
    Index = 'index'


def get_api_key():
    val = os.getenv('MINERU_API_KEY', None)
    if val is None:
        raise ValueError('MINERU_API_KEY is not set')
    return val

API_KEY = get_api_key()

def convert_pdf_bytes_to_bytes_by_pymupdf(pdf_bytes, start_page_id=0, end_page_id=None):
    document = fitz.open('pdf', pdf_bytes)
    output_document = fitz.open()
    end_page_id = (
        end_page_id
        if end_page_id is not None and end_page_id >= 0
        else len(document) - 1
    )
    if end_page_id > len(document) - 1:
        print('end_page_id is out of range, use pdf_docs length')
        end_page_id = len(document) - 1
    output_document.insert_pdf(document, from_page=start_page_id, to_page=end_page_id)
    output_bytes = output_document.tobytes()
    return output_bytes


def compress_directory_to_zip(directory_path, output_zip_path):
    os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:

            # 遍历目录中的所有文件和子目录
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    # 构建完整的文件路径
                    file_path = os.path.join(root, file)
                    # 计算相对路径
                    arcname = os.path.relpath(file_path, directory_path)
                    # 添加文件到 ZIP 文件
                    zipf.write(file_path, arcname)
        return 0
    except Exception as e:
        print(str(e))
        return -1


def generate_random_string(length=32):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def draw_bbox_with_number(i, bbox_list, page, rgb_config, fill_config, draw_bbox=True):
    new_rgb = []
    for item in rgb_config:
        item = float(item) / 255
        new_rgb.append(item)
    page_data = bbox_list[i]
    for j, bbox in enumerate(page_data):
        x0, y0, x1, y1 = bbox
        rect_coords = fitz.Rect(x0, y0, x1, y1)  # Define the rectangle
        if draw_bbox:
            if fill_config:
                page.draw_rect(
                    rect_coords,
                    color=None,
                    fill=new_rgb,
                    fill_opacity=0.3,
                    width=0.5,
                    overlay=True,
                )  # Draw the rectangle
            else:
                page.draw_rect(
                    rect_coords,
                    color=new_rgb,
                    fill=None,
                    fill_opacity=1,
                    width=0.5,
                    overlay=True,
                )  # Draw the rectangle
        page.insert_text(
            (x1 + 2, y0 + 10), str(j + 1), fontsize=10, color=new_rgb
        )  # Insert the index in the top left corner of the rectangle

def draw_bbox_without_number(i, bbox_list, page, rgb_config, fill_config):
    new_rgb = []
    for item in rgb_config:
        item = float(item) / 255
        new_rgb.append(item)
    page_data = bbox_list[i]
    for bbox in page_data:
        x0, y0, x1, y1 = bbox
        rect_coords = fitz.Rect(x0, y0, x1, y1)  # Define the rectangle
        if fill_config:
            page.draw_rect(
                rect_coords,
                color=None,
                fill=new_rgb,
                fill_opacity=0.3,
                width=0.5,
                overlay=True,
            )  # Draw the rectangle
        else:
            page.draw_rect(
                rect_coords,
                color=new_rgb,
                fill=None,
                fill_opacity=1,
                width=0.5,
                overlay=True,
            )  # Draw the rectangle

def draw_layout_bbox(pdf_info, pdf_bytes, output_path):
    dropped_bbox_list = []
    tables_list, tables_body_list = [], []
    tables_caption_list, tables_footnote_list = [], []
    imgs_list, imgs_body_list, imgs_caption_list = [], [], []
    imgs_footnote_list = []
    titles_list = []
    texts_list = []
    interequations_list = []
    lists_list = []
    indexs_list = []
    for page in pdf_info:

        page_dropped_list = []
        tables, tables_body, tables_caption, tables_footnote = [], [], [], []
        imgs, imgs_body, imgs_caption, imgs_footnote = [], [], [], []
        titles = []
        texts = []
        interequations = []
        lists = []
        indices = []

        for dropped_bbox in page['discarded_blocks']:
            page_dropped_list.append(dropped_bbox['bbox'])
        dropped_bbox_list.append(page_dropped_list)
        for block in page['para_blocks']:
            bbox = block['bbox']
            if block['type'] == BlockType.Table:
                tables.append(bbox)
                for nested_block in block['blocks']:
                    bbox = nested_block['bbox']
                    if nested_block['type'] == BlockType.TableBody:
                        tables_body.append(bbox)
                    elif nested_block['type'] == BlockType.TableCaption:
                        tables_caption.append(bbox)
                    elif nested_block['type'] == BlockType.TableFootnote:
                        tables_footnote.append(bbox)
            elif block['type'] == BlockType.Image:
                imgs.append(bbox)
                for nested_block in block['blocks']:
                    bbox = nested_block['bbox']
                    if nested_block['type'] == BlockType.ImageBody:
                        imgs_body.append(bbox)
                    elif nested_block['type'] == BlockType.ImageCaption:
                        imgs_caption.append(bbox)
                    elif nested_block['type'] == BlockType.ImageFootnote:
                        imgs_footnote.append(bbox)
            elif block['type'] == BlockType.Title:
                titles.append(bbox)
            elif block['type'] == BlockType.Text:
                texts.append(bbox)
            elif block['type'] == BlockType.InterlineEquation:
                interequations.append(bbox)
            elif block['type'] == BlockType.List:
                lists.append(bbox)
            elif block['type'] == BlockType.Index:
                indices.append(bbox)

        tables_list.append(tables)
        tables_body_list.append(tables_body)
        tables_caption_list.append(tables_caption)
        tables_footnote_list.append(tables_footnote)
        imgs_list.append(imgs)
        imgs_body_list.append(imgs_body)
        imgs_caption_list.append(imgs_caption)
        imgs_footnote_list.append(imgs_footnote)
        titles_list.append(titles)
        texts_list.append(texts)
        interequations_list.append(interequations)
        lists_list.append(lists)
        indexs_list.append(indices)

    layout_bbox_list = []

    table_type_order = {
        'table_caption': 1,
        'table_body': 2,
        'table_footnote': 3
    }
    for page in pdf_info:
        page_block_list = []
        for block in page['para_blocks']:
            if block['type'] in [
                BlockType.Text,
                BlockType.Title,
                BlockType.InterlineEquation,
                BlockType.List,
                BlockType.Index,
            ]:
                bbox = block['bbox']
                page_block_list.append(bbox)
            elif block['type'] in [BlockType.Image]:
                for sub_block in block['blocks']:
                    bbox = sub_block['bbox']
                    page_block_list.append(bbox)
            elif block['type'] in [BlockType.Table]:
                sorted_blocks = sorted(block['blocks'], key=lambda x: table_type_order[x['type']])
                for sub_block in sorted_blocks:
                    bbox = sub_block['bbox']
                    page_block_list.append(bbox)

        layout_bbox_list.append(page_block_list)

    pdf_docs = fitz.open('pdf', pdf_bytes)

    for i, page in enumerate(pdf_docs):

        draw_bbox_without_number(i, dropped_bbox_list, page, [158, 158, 158], True)
        # draw_bbox_without_number(i, tables_list, page, [153, 153, 0], True)  # color !
        draw_bbox_without_number(i, tables_body_list, page, [204, 204, 0], True)
        draw_bbox_without_number(i, tables_caption_list, page, [255, 255, 102], True)
        draw_bbox_without_number(i, tables_footnote_list, page, [229, 255, 204], True)
        # draw_bbox_without_number(i, imgs_list, page, [51, 102, 0], True)
        draw_bbox_without_number(i, imgs_body_list, page, [153, 255, 51], True)
        draw_bbox_without_number(i, imgs_caption_list, page, [102, 178, 255], True)
        draw_bbox_without_number(i, imgs_footnote_list, page, [255, 178, 102], True),
        draw_bbox_without_number(i, titles_list, page, [102, 102, 255], True)
        draw_bbox_without_number(i, texts_list, page, [153, 0, 76], True)
        draw_bbox_without_number(i, interequations_list, page, [0, 255, 0], True)
        draw_bbox_without_number(i, lists_list, page, [40, 169, 92], True)
        draw_bbox_without_number(i, indexs_list, page, [40, 169, 92], True)

        draw_bbox_with_number(
            i, layout_bbox_list, page, [255, 0, 0], False, draw_bbox=False
        )

    # Save the PDF
    pdf_docs.save(output_path)


def request_remote_parse(file_path, is_ocr=True, layout_mode='doclayout_yolo', formula_enable=True, table_enable=True, language='en'):
    URL_ENDPOINT = 'https://mineru.net/api/v4/file-urls/batch'
    header = {
        'Content-Type':'application/json',
        "Authorization":f"Bearer {API_KEY}"
    }
    data = {
        "enable_formula": formula_enable,
        "language": language,
        "layout_model": layout_mode,
        "enable_table": table_enable,
        "files": [
            {"name":file_path, "is_ocr": is_ocr, "data_id": generate_random_string()}
        ]
    }
    file_path = file_path
    
    response = requests.post(URL_ENDPOINT, headers=header, json=data)
    if response.status_code == 200:
        result = response.json()
        print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            print('batch_id:{},urls:{}'.format(batch_id, urls))
            with open(file_path, 'rb') as f:
                res_upload = requests.put(urls[0], data=f)
            if res_upload.status_code == 200:
                print("upload success")
            else:
                print("upload failed")
        else:
            print('apply upload url failed,reason:{}'.format(result))
    else:
        print('response not success. status:{} ,result:{}'.format(response.status_code, response))
    return response


def get_parse_result(batch_id):
    URL_ENDPOINT = f'https://mineru.net/api/v4/extract-results/batch/{batch_id}'
    header = {
        'Content-Type':'application/json',
        "Authorization":f"Bearer {API_KEY}"
    }
    MAX_COUNT = 900
    count = 0
    while True:
        count += 1 
        if count > MAX_COUNT:
            return None, None, None, None
        try:
            res = requests.get(URL_ENDPOINT, headers=header)
            if res.status_code == 200:
                jso = res.json()
                state = jso['data']['extract_result'][0]['state']
                if state != "done":
                    time.sleep(1)
                    continue
                else:
                    zip_file_url = jso['data']['extract_result'][0]['full_zip_url']
                    zip_file_path = os.path.join('./output/zip', f'{batch_id}.zip')
                    extract_dir = os.path.join('./output/extract', batch_id)
                    os.makedirs(os.path.dirname(zip_file_path), exist_ok=True)
                    os.makedirs(extract_dir, exist_ok=True)
                    
                    # Download zip file
                    with open(zip_file_path, 'wb') as f:
                        f.write(requests.get(zip_file_url).content)
                    
                    # Extract zip file
                    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    
                    # Find the markdown file
                    md_file = None
                    for root, _, files in os.walk(extract_dir):
                        for file in files:
                            if file.endswith('.md'):
                                md_file = os.path.join(root, file)
                                break
                        if md_file:
                            break

                    orig_pdf_file = None
                    for root, _, files in os.walk(extract_dir):
                        for file in files:
                            if file.endswith('.pdf'):
                                orig_pdf_file = os.path.join(root, file)
                                break
                        if orig_pdf_file:
                            break

                    if md_file:
                        with open(md_file, 'r', encoding='utf-8') as f:
                            txt_content = f.read()
                        md_content = replace_image_with_base64(txt_content, os.path.dirname(md_file))
                        with open(os.path.join(extract_dir, 'layout.json')) as f:
                            pdf_info = json.load(f)
                        return orig_pdf_file.replace('_origin.pdf', '_layout.pdf'), md_content, txt_content, pdf_info['pdf_info']
                    else:
                        print(f"No markdown file found in {extract_dir}")
                        return None, None, None, None
            else:
                print(f'get parse result failed, status: {res.status_code}')

        except Exception as e:
            print(str(e))
            time.sleep(1)


def image_to_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def replace_image_with_base64(markdown_text, image_dir_path):
    # 匹配Markdown中的图片标签
    pattern = r'\!\[(?:[^\]]*)\]\(([^)]+)\)'

    # 替换图片链接
    def replace(match):
        relative_path = match.group(1)
        full_path = os.path.join(image_dir_path, relative_path)
        base64_image = image_to_base64(full_path)
        return f'![{relative_path}](data:image/jpeg;base64,{base64_image})'
    
    # 应用替换
    return re.sub(pattern, replace, markdown_text)


def to_markdown(file_path, end_pages, is_ocr, layout_mode, formula_enable, table_enable, language):
    file_path = to_pdf(file_path, end_pages)
    with open(file_path, 'rb') as f:
        pdf_bytes = f.read()
    # Request remote parsing
    response = request_remote_parse(file_path, is_ocr, layout_mode, formula_enable, table_enable, language)
    if response.status_code != 200:
        return "Error: Failed to request parsing", "", None, None
    
    json_data = response.json()
    if json_data["code"] != 0:
        return f"Error: {json_data.get('msg', 'Unknown error')}", "", None, None
    
    batch_id = json_data['data']['batch_id']
    
    # Get and process results
    new_pdf_path, md_content, txt_content, layout_info = get_parse_result(batch_id)
    if md_content is None:
        return "Error: Failed to get results", "", None, None
    draw_layout_bbox(layout_info, pdf_bytes, new_pdf_path)
    zip_path = os.path.join('./archive', f'{batch_id}.zip')
    compress_directory_to_zip(os.path.dirname(new_pdf_path), zip_path)
    return md_content, txt_content, zip_path, new_pdf_path


latex_delimiters = [{'left': '$$', 'right': '$$', 'display': True},
                    {'left': '$', 'right': '$', 'display': False}]


header_path = os.path.join(os.path.dirname(__file__), 'header.html')
with open(header_path, 'r') as file:
    header = file.read()


latin_lang = [
        'af', 'az', 'bs', 'cs', 'cy', 'da', 'de', 'es', 'et', 'fr', 'ga', 'hr',  # noqa: E126
        'hu', 'id', 'is', 'it', 'ku', 'la', 'lt', 'lv', 'mi', 'ms', 'mt', 'nl',
        'no', 'oc', 'pi', 'pl', 'pt', 'ro', 'rs_latin', 'sk', 'sl', 'sq', 'sv',
        'sw', 'tl', 'tr', 'uz', 'vi', 'french', 'german'
]
arabic_lang = ['ar', 'fa', 'ug', 'ur']
cyrillic_lang = [
        'ru', 'rs_cyrillic', 'be', 'bg', 'uk', 'mn', 'abq', 'ady', 'kbd', 'ava',  # noqa: E126
        'dar', 'inh', 'che', 'lbe', 'lez', 'tab'
]
devanagari_lang = [
        'hi', 'mr', 'ne', 'bh', 'mai', 'ang', 'bho', 'mah', 'sck', 'new', 'gom',  # noqa: E126
        'sa', 'bgc'
]
other_lang = ['en', 'ch', 'korean', 'japan', 'chinese_cht', 'ta', 'te', 'ka']

all_lang = ['']
all_lang.extend([*other_lang, *latin_lang, *arabic_lang, *cyrillic_lang, *devanagari_lang])


def to_pdf(file_path, end_pages):
    unique_filename = f'{uuid.uuid4()}.pdf'
    tmp_file_path = os.path.join(os.path.dirname(file_path), unique_filename)

    with pymupdf.open(file_path) as f:
        if f.is_pdf:
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
        else:
            pdf_bytes = f.convert_to_pdf()
            # 将pdfbytes 写入到uuid.pdf中
            # 生成唯一的文件名
        doc = fitz.open("pdf", pdf_bytes)
        if end_pages is None:
            end_pages = len(doc)
        else:
            end_pages = min(end_pages, len(doc))

        pdf_bytes = convert_pdf_bytes_to_bytes_by_pymupdf(pdf_bytes, 0, end_pages-1)
            # 将字节数据写入文件
        with open(tmp_file_path, 'wb') as tmp_pdf_file:
            tmp_pdf_file.write(pdf_bytes)

        return tmp_file_path


def main():
    with gr.Blocks() as demo:
        gr.HTML(header)
        with gr.Row():
            with gr.Column(variant='panel', scale=5):
                file = gr.File(label='Please upload a PDF or image', file_types=['.pdf', '.png', '.jpeg', '.jpg'])
                max_pages = gr.Slider(1, 600, 10, step=1, label='Max convert pages', value=10)
                with gr.Row():
                    layout_mode = gr.Dropdown(['layoutlmv3', 'doclayout_yolo'], label='Layout model', value='doclayout_yolo')
                    language = gr.Dropdown(all_lang, label='Language', value='en')
                with gr.Row():
                    formula_enable = gr.Checkbox(label='Enable formula recognition', value=True)
                    is_ocr = gr.Checkbox(label='Force enable OCR', value=False)
                    table_enable = gr.Checkbox(label='Enable table recognition(test)', value=True)
                with gr.Row():
                    change_bu = gr.Button('Convert')
                    clear_bu = gr.ClearButton(value='Clear')
                pdf_show = PDF(label='PDF preview', interactive=False, visible=True, height=800)
                with gr.Accordion('Examples:'):
                    example_root = os.path.join(os.path.dirname(__file__), 'examples')
                    gr.Examples(
                        examples=[os.path.join(example_root, _) for _ in os.listdir(example_root) if
                                  _.endswith('pdf')],
                        inputs=file
                    )

            with gr.Column(variant='panel', scale=5):
                output_file = gr.File(label='convert result', interactive=False)
                with gr.Tabs():
                    with gr.Tab('Markdown rendering'):
                        md = gr.Markdown(label='Markdown rendering', height=1100, show_copy_button=True,
                                         latex_delimiters=latex_delimiters, line_breaks=True)
                    with gr.Tab('Markdown text'):
                        md_text = gr.TextArea(lines=45, show_copy_button=True)
        file.change(fn=to_pdf, inputs=file, outputs=pdf_show)
        change_bu.click(fn=to_markdown, inputs=[file, max_pages, is_ocr, layout_mode, formula_enable, table_enable, language],
                        outputs=[md, md_text, output_file, pdf_show])
        clear_bu.add([file, md, pdf_show, md_text, output_file, is_ocr])

    demo.launch(server_name='0.0.0.0')


if __name__ == '__main__':
    main()

