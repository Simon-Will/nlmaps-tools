# -*- coding: utf-8 -*-
"""Contains the superclass MRL for basic handling of a MRL formula that is not closer defined
    as well as subclasses for specific MRL languages"""
import collections
import re
import tempfile
import shutil
import subprocess
import os


class MRL:
    """Superclass that implements basic functions one might want to apply to a MRL formula"""
    def __init__(self):
        """
        Initializes a generic MRL object for pre- & postprocessing
        """
        self.mrl_type = 'MRL'

    def preprocess_mrl(self, mrl):
        """Preprocessing consists of simple splitting at white space

        :param mrl: the MRL formula to be preprocessed
        :return: the preprocessed MRL formula
        """
        return mrl.split(" ")

    def preprocess_mrl_set(self, mrls):
        """Preprocesses a list of MRL formulae

        :param mrls: a list of MRL formulae
        :return: a preprocessed list of MRL formulae
        """
        preprocessed_set = []
        for mrl in mrls:
            preprocessed_set.append(self.preprocess_mrl(mrl))
        return preprocessed_set

    def delete_first_n_occurences(self, string_to_shorten, element, n):
        while n > 0:
            try:
                #m = re.search(r'\b%s\b' % re.sub(r'([.^$|()\[\]{}*+?\\])', r'\g<1>', element), mrl)
                to_search = '\\b%s\\b' % re.escape(element)
                m = re.search(r'%s' % to_search, string_to_shorten)
                string_to_shorten = string_to_shorten[m.end():]
                n = n - 1
            except:
                return ""
        return string_to_shorten

    def count_arguments(self, s):
        args_found = False
        num_brackets = 0
        num_commas = 0 #equals number of arguments
        i = 0
        while i < len(s) and ((not args_found and num_brackets == 0) or (args_found and num_brackets > 0)):
            c = s[i:i + 1]
            if c == '(':
                args_found = True
                num_brackets += 1
            elif c == ')':
                num_brackets -= 1
            elif num_brackets == 1 and c == ',':
                num_commas += 1
            elif num_brackets < 1 and c == ',':
                break
            i += 1
        if args_found:
            return num_commas + 1
        else:
            assert num_commas == 0
            return 0
        return num_commas

    def delete_spaces(self, mrl):
        quotes_seen = 0
        new_chars = []
        for c in mrl:
            if c == "'":
                quotes_seen += 1
            if c != ' ' or quotes_seen % 2 != 0:
                new_chars.append(c)

        return ''.join(new_chars)


class NLmaps(MRL):
    """Overrides MRL functions to work specifically for the NLmaps MRL"""
    def __init__(self, cdec = None, query_db = None, db_dir = None):
        """
        Initializes a NLmaps MRL object for pre- & postprocessing
        """
        self.mrl_type = 'MRL'
        self.cdec = cdec
        self.query_db = query_db
        self.db_dir = db_dir

    def preprocess_mrl(self, mrl):
        """Preprocessing for a NLmaps MRL formula

        :param mrl: the sentence to be preprocessed
        :return: the preprocessed sentence
        """
        # sequence of characters that does not contain ( or ) : [^\\(\\)]
        mrl = re.sub(r"(','[^\(\)]*?),([^\(\)]*?')", "\g<1>SAVECOMMA\g<2>", mrl)
        # need to protect brackets that occur in values, assumes that there is at most one open ( and 1 close)
        mrl = re.sub(r",' *([^\(\)]*?)\((.*?) *'\)", ",'\g<1>BRACKETOPEN\g<2>')", mrl)
        mrl = re.sub(r",' *([^\(\)]*?)\)([^\(\)]*?) *'\)", ",'\g<1>BRACKETCLOSE\g<2>')", mrl)
        mrl = mrl.replace(" ", "€")
        mrl = re.sub(r"(?<=([^,\(\)]))'(?=([^,\(\)]))", "SAVEAPO", mrl)
        mrl = re.sub(r"and\(' *([^\(\)]+?) *',' *([^\(\)]+?) *'\)", "and(\g<1>@s','\g<2>@s)",
                     mrl)  # for when a and() surrounds two end values
        mrl = re.sub(r"\(' *([^\(\)]+?) *'\)", "(\g<1>@s)",
                     mrl)  # a bracket ( or ) is not allowed withing any key or value
        mrl = re.sub(r"([,\)\(])or\(([^\(\)]+?)','([^\(\)]+?)@s\)", "\g<1>or(\g<2>@s','\g<3>@s)",
                     mrl)  # for when a or() surrounds two values
        mrl = re.sub(r"\s+", " ", mrl)
        mrl = re.sub(r"'", "", mrl)
        mrl = mrl.strip()
        mrl = self.linearise(mrl)
        return mrl

    def linearise(self, mrl):
        """Linearises a NLmaps MRL formula. For example:
        query(area(keyval('name','City of Edinburgh')),nwr(keyval('amenity','police')),qtype(least(topx(1))))
        becomes
        query@3 area@1 keyval@2 name@0 City€of€Edinburgh@s nwr@1 keyval@2 amenity@0 police@s qtype@1 least@1 topx@1 1@0

        :param mrl: the sentence to be linearised
        :return: the linearised sentence
        """
        just_words = mrl
        just_words = just_words.replace("(", " ")
        just_words = just_words.replace(")", " ")
        just_words = just_words.replace(",", " ")
        just_words = re.sub(r"\s+", " ", just_words)
        just_words = just_words.strip()
        lin = []
        seen_string_x_times = collections.defaultdict(lambda:0)
        for element in just_words.split(" "):
            seen_string_x_times[element] += 1
            if element.endswith("@s"):
                lin.append(element)
                continue
            shortened_string = self.delete_first_n_occurences(mrl, element, seen_string_x_times[element])
            args = self.count_arguments(shortened_string)
            lin.append("%s@%s" % (element, args))
        return ' '.join(lin)

    def insert_pass_through_words(self, lin, non_stemmed, stemmed):
        non_stemmed = non_stemmed.split(" ")
        stemmed = stemmed.split(" ")
        if len(non_stemmed) != len(stemmed):
            return lin
        for i, element in enumerate(lin):
            word_pos = -1
            if "@" not in element:
                for j, stemmed_element in enumerate(stemmed):
                    if element == stemmed_element: #then word was passed through
                        word_pos = j
                    if word_pos is not -1:
                        lin[i] = "%s@s" % non_stemmed[word_pos]
                        word_pos = -1
        return lin

    def transform_if_tree(self, lin):
        stack_arity = []
        mrl = []
        prev = ""

        for element in lin:
            if "@" not in element: #else invalid
                return ""
            element, arity = element.rsplit("@")
            arity_s_found = False
            if arity == "s":
                arity = 0
                arity_s_found = True
            else:
                try:
                    arity = int(arity)
                except:
                    return ""
            if arity > 0:
                mrl.append(element)
                mrl.append("(")
                stack_arity.append(arity)
            else:
                if arity_s_found and len(stack_arity) is 0:
                    return ""
                if arity_s_found or prev == "keyval" or prev == "findkey":
                    element = element.replace("€", " ")
                    element = "'%s'" % element
                mrl.append(element)
                while len(stack_arity) > 0:
                    top = stack_arity.pop()
                    if top > 1:
                        mrl.append(",")
                        stack_arity.append(top-1)
                        break
                    else:
                        mrl.append(")")
            prev = element
        if len(stack_arity) is not 0:
            return ""
        return ''.join(mrl)

    def check_MRL_tree(self, mrl, cfg):
        if self.cdec is None: return False
        temp_dir = tempfile.mkdtemp("", "semparse_functionalizer")
        try:
            mrl = mrl.replace("(", "( ")
            mrl = mrl.replace(",", " , ")
            mrl = mrl.replace(")", " )")
            mrl = re.sub(r"name:.*? \)", "name:lg )", mrl)
            mrl = re.sub(r"keyval\( '([^\(\)]+?)' , '[^\(\)]+?' ", "keyval( '\g<1>' , 'valvariable' ", mrl)
            mrl = re.sub(r"keyval\( '([^\(\)]+?)' , or\( '[^\(\)]+?' , '[^\(\)]+?' ", "keyval( '$1' , or( 'valvariable' , 'valvariable' ", mrl)
            mrl = re.sub(r"keyval\( '([^\(\)]+?)' , and\( '[^\(\)]+?' , '[^\(\)]+?' ", "keyval( '$1' , and( 'valvariable' , 'valvariable' ", mrl)
            mrl = re.sub(r" '(.*?)' ", " ' \g<1> ' ", mrl)
            m = re.search("topx\( (.*?) \)", mrl)
            if m:
                new_number = ""
                for digit in m.group(1):
                    new_number = new_number + digit + " "
                    mrl = re.sub(r"topx\( (.*?)\)", r"topx( " + new_number + ")", mrl)
            m = re.search("maxdist\( (.*?) \)", mrl)
            if m:
                new_number = ""
                for digit in m.group(1):
                    new_number = new_number + digit + " "
                    mrl = re.sub(r"maxdist\( (.*?)\)", r"maxdist( " + new_number + ")", mrl)
            ini_file = open('%s/cdec_validate.ini' % temp_dir, 'w')
            print >>ini_file, "formalism=scfg"
            print >>ini_file, "intersection_strategy=cube_pruning"
            print >>ini_file, "cubepruning_pop_limit=1000"
            print >>ini_file, "grammar=%s" % cfg
            print >>ini_file, "scfg_max_span_limit=1000"
            ini_file.close()
            args = ["%s/decoder/cdec" % self.cdec,
                    '-c', '%s/cdec_validate.ini' % (temp_dir)]
            infile = open('%s/sent.tmp' % temp_dir, 'w')
            print >>infile, mrl
            infile.close()
            infile = open('%s/sent.tmp' % temp_dir, 'r')
            nullfile = open(os.devnull, 'w')
            p = subprocess.Popen(args, stdin=infile, stdout=nullfile, stderr=subprocess.PIPE)
            cfg_log = p.stderr.read()
            infile.close()
            nullfile.close()
            shutil.rmtree(temp_dir)
            if "NO PARSE" in cfg_log:
                return False
            return True
        except:
            shutil.rmtree(temp_dir)
        return False

    def functionalise(self, lin, non_stemmed = None, stemmed = None, cfg = None):
        """Functionalises a NLmaps MRL formula. For example:
        query@3 area@1 keyval@2 name@0 City€of€Edinburgh@s nwr@1 keyval@2 amenity@0 police@s qtype@1 least@1 topx@1 1@0
        becomes
        query(area(keyval('name','City of Edinburgh')),nwr(keyval('amenity','police')),qtype(least(topx(1))))

        :param mrl: the sentence to be functionalised
        :return: the functionalised sentence
        """
        lin = lin.replace("<topx>", "")
        lin = lin.replace("</topx>", "@0")
        lin = lin.split(" ")

        if non_stemmed is not None and stemmed is not None:
            lin = self.insert_pass_through_words(lin, non_stemmed, stemmed)

        mrl = self.transform_if_tree(lin)
        if mrl == "":
            return ""

        if cfg is not None:
            bool_valid_under_CFG = self.check_MRL_tree(mrl, cfg)
            if not bool_valid_under_CFG:
                return ""

        mrl = mrl.replace("SAVEAPO", "'")
        mrl = mrl.replace("BRACKETOPEN", "(")
        mrl = mrl.replace("BRACKETCLOSE", ")")
        mrl = mrl.replace("SAVECOMMA", ",")
        return mrl


MRLS = collections.OrderedDict([
    ('', MRL),
    ('nlmaps', NLmaps)
])
