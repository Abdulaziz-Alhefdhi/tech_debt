import string
from random import sample
import sys
import numpy as np
import pickle



def extract_data(data_path):
    # Retrieve data from files
    print("Retrieving data from disk...")
    with open(data_path + 'ast_seqs.txt', 'r', encoding='utf-8') as f:
        draft_input_lines = f.read().split('\n')
    with open(data_path + 'labels.txt', 'r', encoding='utf-8') as f:
        draft_label_lines = f.read().split('\n')
    with open(data_path + 'comments.txt', 'r', encoding='utf-8') as f:
        draft_comment_lines = f.read().split('\n')
    with open(data_path + 'codes.txt', 'r', encoding='utf-8') as f:
        draft_code_lines = f.read().split('\n')
    # Remove last (empty) items
    draft_input_lines   = draft_input_lines[:-1]
    draft_label_lines   = draft_label_lines[:-1]
    draft_comment_lines = draft_comment_lines[:-1]
    draft_code_lines    = draft_code_lines[:-1]

    # Ignore non-English data
    input_lines, label_lines, comment_lines, code_lines = [], [], [], []
    c = 0
    for inp_ln, lbl_ln, com_ln, cod_ln in zip(draft_input_lines, draft_label_lines, draft_comment_lines, draft_code_lines):
        match = False
        for char in string.ascii_letters:
            if char in com_ln:
                match = True
                input_lines.append(inp_ln)
                label_lines.append(lbl_ln)
                comment_lines.append(com_ln)
                code_lines.append(cod_ln)
                break
        if not match:
            c += 1
    print(c, "comments do not contain English text at all")

    # Combine data to remove duplicates
    aggregated = []
    for inp_ln, lbl_ln, com_ln, cod_ln in zip(input_lines, label_lines, comment_lines, code_lines):
        aggregated.append((inp_ln, lbl_ln, com_ln, cod_ln))
    # Remove duplicates
    aggregated = set(aggregated)
    # Re-order data (pos before neg)
    dataset = []
    for item in aggregated:
        if item[1] == "1":
            dataset.append(item)
    for item in aggregated:
        if item[1] == "0":
            dataset.append(item)

    return dataset


# Get data
def retrieve_data(data_path, num_samples, max_input_length, max_comment_length):
    if num_samples % 2 != 0:
        sys.exit("Error: num_samples must be an even number")

    dataset = extract_data(data_path)

    # AST sequences
    print("Treating code sequences...")
    draft_input_lists = []
    for item in dataset:
        input_list = item[0].replace("(", " ( ")
        input_list = input_list.replace(")", " ) ")
        input_list = input_list.replace("_", " _ ")
        draft_input_lists.append(input_list.split())

    # Labels to int
    draft_labels = []
    for item in dataset:
        if item[1] == "1":
            draft_labels.append(1)
        else:
            draft_labels.append(0)

    # Comments
    print("Deleting non-English characters from comments...")
    draft_comment_lists = []
    for item in dataset:
        txt = item[2]
        for char in txt:
            if char not in string.ascii_letters:
                txt = txt.replace(char, " ")
        draft_comment_lists.append(txt.lower().split())
    # Add start and end symbols to target lists
    for i in range(len(draft_comment_lists)):
        draft_comment_lists[i] = ["<sos>"] + draft_comment_lists[i] + ["<eos>"]

    # Codes
    draft_code_lines = []
    for item in dataset:
        draft_code_lines.append(item[3])

    # Remove too-long codes and comments
    input_lists, labels, comment_lists, code_lines = [], [], [], []
    for il, lbl, cl, co in zip(draft_input_lists, draft_labels, draft_comment_lists, draft_code_lines):
        if len(il) <= max_input_length and len(cl) <= max_comment_length:
            input_lists.append(il)
            labels.append(lbl)
            comment_lists.append(cl)
            code_lines.append(co)

    # Separate positive from negative
    pos_data, neg_data = [], []
    for il, lbl, cl, co in zip(input_lists, labels, comment_lists, code_lines):
        if lbl == 1:
            pos_data.append((il, lbl, cl, co))
        else:
            neg_data.append((il, lbl, cl, co))

    # Clean, shuffle, and cut negative data
    # Lengths as in positive data
    max_pos_seq = max([len(x[0]) for x in pos_data])
    max_pos_com = max([len(x[2]) for x in pos_data])
    clean_neg_data = []
    for item in neg_data:
        if len(item[0]) <= max_pos_seq and len(item[2]) <= max_pos_com:
            clean_neg_data.append(item)
    neg_data = sample(clean_neg_data, k=len(clean_neg_data))  # Shuffle
    neg_data = neg_data[:len(pos_data)]  # Cut

    # Use num_samples or less, deducting form positive and negative data equally
    pos_data = sample(pos_data, k=len(pos_data))  # Shuffle positive data
    pos_data = pos_data[: min(num_samples//2, len(pos_data))]
    neg_data = neg_data[: min(num_samples//2, len(neg_data))]

    print("Creating final version of dataset...")
    input_lists, labels, comment_lists, code_lines = [], [], [], []
    for item in pos_data:
        input_lists.append(item[0])
        labels.append(item[1])
        comment_lists.append(item[2])
        code_lines.append(item[3])
    for item in neg_data:
        input_lists.append(item[0])
        labels.append(item[1])
        comment_lists.append(item[2])
        code_lines.append(item[3])

    return np.array(input_lists), np.array(labels), np.array(comment_lists), np.array(code_lines)


def tokenize(array):
    vocab = set()
    for seq in array:
        for token in seq:
            vocab.add(token)
    return sorted(list(vocab)) + ["<unknown>"]


class DataObject:
    def __init__(self, input_lists, labels, comment_lists, code_lines, input_vocab, comment_vocab):
        self.input_lists   = input_lists
        self.labels        = labels
        self.comment_lists = comment_lists
        self.code_lines    = code_lines
        self.input_vocab   = input_vocab
        self.comment_vocab = comment_vocab


def data_shapes(dataset):
    num_encoder_tokens = len(dataset.input_vocab)
    num_decoder_tokens = len(dataset.comment_vocab)
    max_encoder_seq_length = max([len(txt) for txt in dataset.input_lists])
    max_decoder_seq_length = max([len(txt) for txt in dataset.comment_lists])
    n_input_samples = len(dataset.input_lists)

    return num_encoder_tokens, num_decoder_tokens, max_encoder_seq_length, max_decoder_seq_length, n_input_samples


def shape_info(n_input_samples, num_encoder_tokens, num_decoder_tokens, max_encoder_seq_length, max_decoder_seq_length):
    print('Number of samples:', n_input_samples)
    print('Number of unique input tokens:', num_encoder_tokens)
    print('Number of unique comment words:', num_decoder_tokens)
    print('Max sequence length for inputs:', max_encoder_seq_length)
    print('Max sequence length for comments:', max_decoder_seq_length)


def write_to_disk(data_path, dataset):
    # Input sequences
    with open(data_path + 'ast_seqs.txt', 'w', encoding='utf-8') as f:
        for line in dataset.input_lists:
            f.write(' '.join(line) + '\n')
    # labels
    with open(data_path + 'labels.txt', 'w', encoding='utf-8') as f:
        for item in dataset.labels:
            f.write(str(item) + '\n')
    # comments
    with open(data_path + 'comments.txt', 'w', encoding='utf-8') as f:
        for line in dataset.comment_lists:
            f.write(' '.join(line) + '\n')
    # Conditional statements
    with open(data_path + 'codes.txt', 'w', encoding='utf-8') as f:
        for line in dataset.code_lines:
            f.write(line + '\n')
    # Input vocabulary
    with open(data_path + 'input_vocab.txt', 'w', encoding='utf-8') as f:
        for line in dataset.input_vocab:
            f.write(line + '\n')
    # Comment vocabulary
    with open(data_path + 'comment_vocab.txt', 'w', encoding='utf-8') as f:
        for line in dataset.comment_vocab:
            f.write(line + '\n')
    # Save the dataset object
    with open(data_path + 'dataset.pkl', 'wb') as f:
        pickle.dump(dataset, f)
