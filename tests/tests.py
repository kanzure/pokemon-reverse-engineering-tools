# -*- coding: utf-8 -*-

import os
from copy import copy
import hashlib
import random
import json

from pokemontools.interval_map import IntervalMap
from pokemontools.chars import chars, jap_chars

from pokemontools.romstr import (
    RomStr,
    AsmList,
)

from pokemontools.item_constants import (
    item_constants,
    find_item_label_by_id,
    generate_item_constants,
)

from pokemontools.pointers import (
    calculate_bank,
    calculate_pointer,
)

from pokemontools.pksv import (
    pksv_gs,
    pksv_crystal,
)

from pokemontools.labels import (
    remove_quoted_text,
    line_has_comment_address,
    line_has_label,
    get_label_from_line,
)

from pokemontools.crystal import (
    rom,
    load_rom,
    rom_until,
    direct_load_rom,
    parse_script_engine_script_at,
    parse_text_engine_script_at,
    parse_text_at2,
    find_all_text_pointers_in_script_engine_script,
    SingleByteParam,
    HexByte,
    MultiByteParam,
    PointerLabelParam,
    ItemLabelByte,
    DollarSignByte,
    DecimalParam,
    rom_interval,
    map_names,
    Label,
    scan_for_predefined_labels,
    all_labels,
    write_all_labels,
    parse_map_header_at,
    old_parse_map_header_at,
    process_00_subcommands,
    parse_all_map_headers,
    translate_command_byte,
    map_name_cleaner,
    load_map_group_offsets,
    load_asm,
    asm,
    is_valid_address,
    index,
    how_many_until,
    grouper,
    get_pokemon_constant_by_id,
    generate_map_constant_labels,
    get_map_constant_label_by_id,
    get_id_for_map_constant_label,
    calculate_pointer_from_bytes_at,
    isolate_incbins,
    process_incbins,
    get_labels_between,
    generate_diff_insert,
    find_labels_without_addresses,
    rom_text_at,
    get_label_for,
    split_incbin_line_into_three,
    reset_incbins,
)

import unittest

class TestCram(unittest.TestCase):
    "this is where i cram all of my unit tests together"

    @classmethod
    def setUpClass(cls):
        global rom
        cls.rom = direct_load_rom()
        rom = cls.rom

    @classmethod
    def tearDownClass(cls):
        del cls.rom

    def test_map_name_cleaner(self):
        name = "hello world"
        cleaned_name = map_name_cleaner(name)
        self.assertNotEqual(name, cleaned_name)
        self.failUnless(" " not in cleaned_name)
        name = "Some Random Pokémon Center"
        cleaned_name = map_name_cleaner(name)
        self.assertNotEqual(name, cleaned_name)
        self.failIf(" " in cleaned_name)
        self.failIf("é" in cleaned_name)

    def test_grouper(self):
        data = range(0, 10)
        groups = grouper(data, count=2)
        self.assertEquals(len(groups), 5)
        data = range(0, 20)
        groups = grouper(data, count=2)
        self.assertEquals(len(groups), 10)
        self.assertNotEqual(data, groups)
        self.assertNotEqual(len(data), len(groups))

    def test_calculate_bank(self):
        self.failUnless(calculate_bank(0x8000) == 2)
        self.failUnless(calculate_bank("0x9000") == 2)
        self.failUnless(calculate_bank(0) == 0)
        for address in [0x4000, 0x5000, 0x6000, 0x7000]:
            self.assertRaises(Exception, calculate_bank, address)

    def test_calculate_pointer(self):
        # for offset <= 0x4000
        self.assertEqual(calculate_pointer(0x0000), 0x0000)
        self.assertEqual(calculate_pointer(0x3FFF), 0x3FFF)
        # for 0x4000 <= offset <= 0x7FFFF
        self.assertEqual(calculate_pointer(0x430F, bank=5), 0x1430F)
        # for offset >= 0x7FFF
        self.assertEqual(calculate_pointer(0x8FFF, bank=6), calculate_pointer(0x8FFF, bank=7))

    def test_translate_command_byte(self):
        self.failUnless(translate_command_byte(crystal=0x0) == 0x0)
        self.failUnless(translate_command_byte(crystal=0x10) == 0x10)
        self.failUnless(translate_command_byte(crystal=0x40) == 0x40)
        self.failUnless(translate_command_byte(gold=0x0) == 0x0)
        self.failUnless(translate_command_byte(gold=0x10) == 0x10)
        self.failUnless(translate_command_byte(gold=0x40) == 0x40)
        self.assertEqual(translate_command_byte(gold=0x0), translate_command_byte(crystal=0x0))
        self.failUnless(translate_command_byte(gold=0x52) == 0x53)
        self.failUnless(translate_command_byte(gold=0x53) == 0x54)
        self.failUnless(translate_command_byte(crystal=0x53) == 0x52)
        self.failUnless(translate_command_byte(crystal=0x52) == None)
        self.assertRaises(Exception, translate_command_byte, None, gold=0xA4)

    def test_pksv_integrity(self):
        "does pksv_gs look okay?"
        self.assertEqual(pksv_gs[0x00], "2call")
        self.assertEqual(pksv_gs[0x2D], "givepoke")
        self.assertEqual(pksv_gs[0x85], "waitbutton")
        self.assertEqual(pksv_crystal[0x00], "2call")
        self.assertEqual(pksv_crystal[0x86], "waitbutton")
        self.assertEqual(pksv_crystal[0xA2], "credits")

    def test_chars_integrity(self):
        self.assertEqual(chars[0x80], "A")
        self.assertEqual(chars[0xA0], "a")
        self.assertEqual(chars[0xF0], "¥")
        self.assertEqual(jap_chars[0x44], "ぱ")

    def test_map_names_integrity(self):
        def map_name(map_group, map_id): return map_names[map_group][map_id]["name"]
        self.assertEqual(map_name(2, 7), "Mahogany Town")
        self.assertEqual(map_name(3, 0x34), "Ilex Forest")
        self.assertEqual(map_name(7, 0x11), "Cerulean City")

    def test_load_map_group_offsets(self):
        addresses = load_map_group_offsets()
        self.assertEqual(len(addresses), 26, msg="there should be 26 map groups")
        addresses = load_map_group_offsets()
        self.assertEqual(len(addresses), 26, msg="there should still be 26 map groups")
        self.assertIn(0x94034, addresses)
        for address in addresses:
            self.assertGreaterEqual(address, 0x4000)
            self.failIf(0x4000 <= address <= 0x7FFF)
            self.failIf(address <= 0x4000)

    def test_index(self):
        self.assertTrue(index([1,2,3,4], lambda f: True) == 0)
        self.assertTrue(index([1,2,3,4], lambda f: f==3) == 2)

    def test_get_pokemon_constant_by_id(self):
        x = get_pokemon_constant_by_id
        self.assertEqual(x(1), "BULBASAUR")
        self.assertEqual(x(151), "MEW")
        self.assertEqual(x(250), "HO_OH")

    def test_find_item_label_by_id(self):
        x = find_item_label_by_id
        self.assertEqual(x(249), "HM_07")
        self.assertEqual(x(173), "BERRY")
        self.assertEqual(x(45), None)

    def test_generate_item_constants(self):
        x = generate_item_constants
        r = x()
        self.failUnless("HM_07" in r)
        self.failUnless("EQU" in r)

    def test_get_label_for(self):
        global all_labels
        temp = copy(all_labels)
        # this is basd on the format defined in get_labels_between
        all_labels = [{"label": "poop", "address": 0x5,
                       "offset": 0x5, "bank": 0,
                       "line_number": 2
                     }]
        self.assertEqual(get_label_for(5), "poop")
        all_labels = temp

    def test_generate_map_constant_labels(self):
        ids = generate_map_constant_labels()
        self.assertEqual(ids[0]["label"], "OLIVINE_POKECENTER_1F")
        self.assertEqual(ids[1]["label"], "OLIVINE_GYM")

    def test_get_id_for_map_constant_label(self):
        global map_internal_ids
        map_internal_ids = generate_map_constant_labels()
        self.assertEqual(get_id_for_map_constant_label("OLIVINE_GYM"), 1)
        self.assertEqual(get_id_for_map_constant_label("OLIVINE_POKECENTER_1F"), 0)

    def test_get_map_constant_label_by_id(self):
        global map_internal_ids
        map_internal_ids = generate_map_constant_labels()
        self.assertEqual(get_map_constant_label_by_id(0), "OLIVINE_POKECENTER_1F")
        self.assertEqual(get_map_constant_label_by_id(1), "OLIVINE_GYM")

    def test_is_valid_address(self):
        self.assertTrue(is_valid_address(0))
        self.assertTrue(is_valid_address(1))
        self.assertTrue(is_valid_address(10))
        self.assertTrue(is_valid_address(100))
        self.assertTrue(is_valid_address(1000))
        self.assertTrue(is_valid_address(10000))
        self.assertFalse(is_valid_address(2097153))
        self.assertFalse(is_valid_address(2098000))
        addresses = [random.randrange(0,2097153) for i in range(0, 9+1)]
        for address in addresses:
            self.assertTrue(is_valid_address(address))

class TestIntervalMap(unittest.TestCase):
    def test_intervals(self):
        i = IntervalMap()
        first = "hello world"
        second = "testing 123"
        i[0:5] = first
        i[5:10] = second
        self.assertEqual(i[0], first)
        self.assertEqual(i[1], first)
        self.assertNotEqual(i[5], first)
        self.assertEqual(i[6], second)
        i[3:10] = second
        self.assertEqual(i[3], second)
        self.assertNotEqual(i[4], first)

    def test_items(self):
        i = IntervalMap()
        first = "hello world"
        second = "testing 123"
        i[0:5] = first
        i[5:10] = second
        results = list(i.items())
        self.failUnless(len(results) == 2)
        self.assertEqual(results[0], ((0, 5), "hello world"))
        self.assertEqual(results[1], ((5, 10), "testing 123"))

class TestRomStr(unittest.TestCase):
    """RomStr is a class that should act exactly like str()
    except that it never shows the contents of it string
    unless explicitly forced"""
    sample_text = "hello world!"
    sample = None

    def setUp(self):
        if self.sample == None:
            self.__class__.sample = RomStr(self.sample_text)

    def test_equals(self):
        "check if RomStr() == str()"
        self.assertEquals(self.sample_text, self.sample)

    def test_not_equal(self):
        "check if RomStr('a') != RomStr('b')"
        self.assertNotEqual(RomStr('a'), RomStr('b'))

    def test_appending(self):
        "check if RomStr()+'a'==str()+'a'"
        self.assertEquals(self.sample_text+'a', self.sample+'a')

    def test_conversion(self):
        "check if RomStr() -> str() works"
        self.assertEquals(str(self.sample), self.sample_text)

    def test_inheritance(self):
        self.failUnless(issubclass(RomStr, str))

    def test_length(self):
        self.assertEquals(len(self.sample_text), len(self.sample))
        self.assertEquals(len(self.sample_text), self.sample.length())
        self.assertEquals(len(self.sample), self.sample.length())

class TestAsmList(unittest.TestCase):
    """AsmList is a class that should act exactly like list()
    except that it never shows the contents of its list
    unless explicitly forced"""

    def test_equals(self):
        base = [1,2,3]
        asm = AsmList(base)
        self.assertEquals(base, asm)
        self.assertEquals(asm, base)
        self.assertEquals(base, list(asm))

    def test_inheritance(self):
        self.failUnless(issubclass(AsmList, list))

    def test_length(self):
        base = range(0, 10)
        asm = AsmList(base)
        self.assertEquals(len(base), len(asm))
        self.assertEquals(len(base), asm.length())
        self.assertEquals(len(base), len(list(asm)))
        self.assertEquals(len(asm), asm.length())

    def test_remove_quoted_text(self):
        x = remove_quoted_text
        self.assertEqual(x("hello world"), "hello world")
        self.assertEqual(x("hello \"world\""), "hello ")
        input = 'hello world "testing 123"'
        self.assertNotEqual(x(input), input)
        input = "hello world 'testing 123'"
        self.assertNotEqual(x(input), input)
        self.failIf("testing" in x(input))

    def test_line_has_comment_address(self):
        x = line_has_comment_address
        self.assertFalse(x(""))
        self.assertFalse(x(";"))
        self.assertFalse(x(";;;"))
        self.assertFalse(x(":;"))
        self.assertFalse(x(":;:"))
        self.assertFalse(x(";:"))
        self.assertFalse(x(" "))
        self.assertFalse(x("".join(" " * 5)))
        self.assertFalse(x("".join(" " * 10)))
        self.assertFalse(x("hello world"))
        self.assertFalse(x("hello_world"))
        self.assertFalse(x("hello_world:"))
        self.assertFalse(x("hello_world:;"))
        self.assertFalse(x("hello_world: ;"))
        self.assertFalse(x("hello_world: ; "))
        self.assertFalse(x("hello_world: ;" + "".join(" " * 5)))
        self.assertFalse(x("hello_world: ;" + "".join(" " * 10)))
        self.assertTrue(x(";1"))
        self.assertTrue(x(";F"))
        self.assertTrue(x(";$00FF"))
        self.assertTrue(x(";0x00FF"))
        self.assertTrue(x("; 0x00FF"))
        self.assertTrue(x(";$3:$300"))
        self.assertTrue(x(";0x3:$300"))
        self.assertTrue(x(";$3:0x300"))
        self.assertTrue(x(";3:300"))
        self.assertTrue(x(";3:FFAA"))
        self.assertFalse(x('hello world "how are you today;0x1"'))
        self.assertTrue(x('hello world "how are you today:0x1";1'))
        returnable = {}
        self.assertTrue(x("hello_world: ; 0x4050", returnable=returnable, bank=5))
        self.assertTrue(returnable["address"] == 0x14050)

    def test_line_has_label(self):
        x = line_has_label
        self.assertTrue(x("hi:"))
        self.assertTrue(x("Hello: "))
        self.assertTrue(x("MyLabel: ; test xyz"))
        self.assertFalse(x(":"))
        self.assertFalse(x(";HelloWorld:"))
        self.assertFalse(x("::::"))
        self.assertFalse(x(":;:;:;:::"))

    def test_get_label_from_line(self):
        x = get_label_from_line
        self.assertEqual(x("HelloWorld: "), "HelloWorld")
        self.assertEqual(x("HiWorld:"), "HiWorld")
        self.assertEqual(x("HiWorld"), None)

    def test_find_labels_without_addresses(self):
        global asm
        asm = ["hello_world: ; 0x1", "hello_world2: ;"]
        labels = find_labels_without_addresses()
        self.failUnless(labels[0]["label"] == "hello_world2")
        asm = ["hello world: ;1", "hello_world: ;2"]
        labels = find_labels_without_addresses()
        self.failUnless(len(labels) == 0)
        asm = None

    def test_get_labels_between(self):
        global asm
        x = get_labels_between#(start_line_id, end_line_id, bank)
        asm = ["HelloWorld: ;1",
               "hi:",
               "no label on this line",
              ]
        labels = x(0, 2, 0x12)
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["label"], "HelloWorld")
        del asm

    # this test takes a lot of time :(
    def xtest_scan_for_predefined_labels(self):
        # label keys: line_number, bank, label, offset, address
        load_asm()
        all_labels = scan_for_predefined_labels()
        label_names = [x["label"] for x in all_labels]
        self.assertIn("GetFarByte", label_names)
        self.assertIn("AddNTimes", label_names)
        self.assertIn("CheckShininess", label_names)

    def test_write_all_labels(self):
        """dumping json into a file"""
        filename = "test_labels.json"
        # remove the current file
        if os.path.exists(filename):
            os.system("rm " + filename)
        # make up some labels
        labels = []
        # fake label 1
        label = {"line_number": 5, "bank": 0, "label": "SomeLabel", "address": 0x10}
        labels.append(label)
        # fake label 2
        label = {"line_number": 15, "bank": 2, "label": "SomeOtherLabel", "address": 0x9F0A}
        labels.append(label)
        # dump to file
        write_all_labels(labels, filename=filename)
        # open the file and read the contents
        file_handler = open(filename, "r")
        contents = file_handler.read()
        file_handler.close()
        # parse into json
        obj = json.read(contents)
        # begin testing
        self.assertEqual(len(obj), len(labels))
        self.assertEqual(len(obj), 2)
        self.assertEqual(obj, labels)

    def test_isolate_incbins(self):
        global asm
        asm = ["123", "456", "789", "abc", "def", "ghi",
               'INCBIN "baserom.gbc",$12DA,$12F8 - $12DA',
               "jkl",
               'INCBIN "baserom.gbc",$137A,$13D0 - $137A']
        lines = isolate_incbins()
        self.assertIn(asm[6], lines)
        self.assertIn(asm[8], lines)
        for line in lines:
            self.assertIn("baserom", line)

    def test_process_incbins(self):
        global incbin_lines, processed_incbins, asm
        incbin_lines = ['INCBIN "baserom.gbc",$12DA,$12F8 - $12DA',
                        'INCBIN "baserom.gbc",$137A,$13D0 - $137A']
        asm = copy(incbin_lines)
        asm.insert(1, "some other random line")
        processed_incbins = process_incbins()
        self.assertEqual(len(processed_incbins), len(incbin_lines))
        self.assertEqual(processed_incbins[0]["line"], incbin_lines[0])
        self.assertEqual(processed_incbins[2]["line"], incbin_lines[1])

    def test_reset_incbins(self):
        global asm, incbin_lines, processed_incbins
        # temporarily override the functions
        global load_asm, isolate_incbins, process_incbins
        temp1, temp2, temp3 = load_asm, isolate_incbins, process_incbins
        def load_asm(): pass
        def isolate_incbins(): pass
        def process_incbins(): pass
        # call reset
        reset_incbins()
        # check the results
        self.assertTrue(asm == [] or asm == None)
        self.assertTrue(incbin_lines == [])
        self.assertTrue(processed_incbins == {})
        # reset the original functions
        load_asm, isolate_incbins, process_incbins = temp1, temp2, temp3

    def test_find_incbin_to_replace_for(self):
        global asm, incbin_lines, processed_incbins
        asm = ['first line', 'second line', 'third line',
               'INCBIN "baserom.gbc",$90,$200 - $90',
               'fifth line', 'last line']
        isolate_incbins()
        process_incbins()
        line_num = find_incbin_to_replace_for(0x100)
        # must be the 4th line (the INBIN line)
        self.assertEqual(line_num, 3)

    def test_split_incbin_line_into_three(self):
        global asm, incbin_lines, processed_incbins
        asm = ['first line', 'second line', 'third line',
               'INCBIN "baserom.gbc",$90,$200 - $90',
               'fifth line', 'last line']
        isolate_incbins()
        process_incbins()
        content = split_incbin_line_into_three(3, 0x100, 10)
        # must end up with three INCBINs in output
        self.failUnless(content.count("INCBIN") == 3)

    def test_analyze_intervals(self):
        global asm, incbin_lines, processed_incbins
        asm, incbin_lines, processed_incbins = None, [], {}
        asm = ['first line', 'second line', 'third line',
               'INCBIN "baserom.gbc",$90,$200 - $90',
               'fifth line', 'last line',
               'INCBIN "baserom.gbc",$33F,$4000 - $33F']
        isolate_incbins()
        process_incbins()
        largest = analyze_intervals()
        self.assertEqual(largest[0]["line_number"], 6)
        self.assertEqual(largest[0]["line"], asm[6])
        self.assertEqual(largest[1]["line_number"], 3)
        self.assertEqual(largest[1]["line"], asm[3])

    def test_generate_diff_insert(self):
        global asm
        asm = ['first line', 'second line', 'third line',
               'INCBIN "baserom.gbc",$90,$200 - $90',
               'fifth line', 'last line',
               'INCBIN "baserom.gbc",$33F,$4000 - $33F']
        diff = generate_diff_insert(0, "the real first line", debug=False)
        self.assertIn("the real first line", diff)
        self.assertIn("INCBIN", diff)
        self.assertNotIn("No newline at end of file", diff)
        self.assertIn("+"+asm[1], diff)

class TestMapParsing(unittest.TestCase):
    def test_parse_all_map_headers(self):
        global parse_map_header_at, old_parse_map_header_at, counter
        counter = 0
        for k in map_names.keys():
            if "offset" not in map_names[k].keys():
                map_names[k]["offset"] = 0
        temp = parse_map_header_at
        temp2 = old_parse_map_header_at
        def parse_map_header_at(address, map_group=None, map_id=None, debug=False):
            global counter
            counter += 1
            return {}
        old_parse_map_header_at = parse_map_header_at
        parse_all_map_headers(debug=False)
        # parse_all_map_headers is currently doing it 2x
        # because of the new/old map header parsing routines
        self.assertEqual(counter, 388 * 2)
        parse_map_header_at = temp
        old_parse_map_header_at = temp2

class TestTextScript(unittest.TestCase):
    """for testing 'in-script' commands, etc."""
    #def test_to_asm(self):
    #    pass # or raise NotImplementedError, bryan_message
    #def test_find_addresses(self):
    #    pass # or raise NotImplementedError, bryan_message
    #def test_parse_text_at(self):
    #    pass # or raise NotImplementedError, bryan_message

class TestEncodedText(unittest.TestCase):
    """for testing chars-table encoded text chunks"""

    def test_process_00_subcommands(self):
        g = process_00_subcommands(0x197186, 0x197186+601, debug=False)
        self.assertEqual(len(g), 42)
        self.assertEqual(len(g[0]), 13)
        self.assertEqual(g[1], [184, 174, 180, 211, 164, 127, 20, 231, 81])

    def test_parse_text_at2(self):
        oakspeech = parse_text_at2(0x197186, 601, debug=False)
        self.assertIn("encyclopedia", oakspeech)
        self.assertIn("researcher", oakspeech)
        self.assertIn("dependable", oakspeech)

    def test_parse_text_engine_script_at(self):
        p = parse_text_engine_script_at(0x197185, debug=False)
        self.assertEqual(len(p.commands), 2)
        self.assertEqual(len(p.commands[0]["lines"]), 41)

    # don't really care about these other two
    def test_parse_text_from_bytes(self): pass
    def test_parse_text_at(self): pass

class TestScript(unittest.TestCase):
    """for testing parse_script_engine_script_at and script parsing in
    general. Script should be a class."""
    #def test_parse_script_engine_script_at(self):
    #    pass # or raise NotImplementedError, bryan_message

    def test_find_all_text_pointers_in_script_engine_script(self):
        address = 0x197637 # 0x197634
        script = parse_script_engine_script_at(address, debug=False)
        bank = calculate_bank(address)
        r = find_all_text_pointers_in_script_engine_script(script, bank=bank, debug=False)
        results = list(r)
        self.assertIn(0x197661, results)

class TestLabel(unittest.TestCase):
    def test_label_making(self):
        line_number = 2
        address = 0xf0c0
        label_name = "poop"
        l = Label(name=label_name, address=address, line_number=line_number)
        self.failUnless(hasattr(l, "name"))
        self.failUnless(hasattr(l, "address"))
        self.failUnless(hasattr(l, "line_number"))
        self.failIf(isinstance(l.address, str))
        self.failIf(isinstance(l.line_number, str))
        self.failUnless(isinstance(l.name, str))
        self.assertEqual(l.line_number, line_number)
        self.assertEqual(l.name, label_name)
        self.assertEqual(l.address, address)

class TestByteParams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_rom()
        cls.address = 10
        cls.sbp = SingleByteParam(address=cls.address)

    @classmethod
    def tearDownClass(cls):
        del cls.sbp

    def test__init__(self):
        self.assertEqual(self.sbp.size, 1)
        self.assertEqual(self.sbp.address, self.address)

    def test_parse(self):
        self.sbp.parse()
        self.assertEqual(str(self.sbp.byte), str(45))

    def test_to_asm(self):
        self.assertEqual(self.sbp.to_asm(), "$2d")
        self.sbp.should_be_decimal = True
        self.assertEqual(self.sbp.to_asm(), str(45))

    # HexByte and DollarSignByte are the same now
    def test_HexByte_to_asm(self):
        h = HexByte(address=10)
        a = h.to_asm()
        self.assertEqual(a, "$2d")

    def test_DollarSignByte_to_asm(self):
        d = DollarSignByte(address=10)
        a = d.to_asm()
        self.assertEqual(a, "$2d")

    def test_ItemLabelByte_to_asm(self):
        i = ItemLabelByte(address=433)
        self.assertEqual(i.byte, 54)
        self.assertEqual(i.to_asm(), "COIN_CASE")
        self.assertEqual(ItemLabelByte(address=10).to_asm(), "$2d")

    def test_DecimalParam_to_asm(self):
        d = DecimalParam(address=10)
        x = d.to_asm()
        self.assertEqual(x, str(0x2d))

class TestMultiByteParam(unittest.TestCase):
    def setup_for(self, somecls, byte_size=2, address=443, **kwargs):
        self.cls = somecls(address=address, size=byte_size, **kwargs)
        self.assertEqual(self.cls.address, address)
        self.assertEqual(self.cls.bytes, rom_interval(address, byte_size, strings=False))
        self.assertEqual(self.cls.size, byte_size)

    def test_two_byte_param(self):
        self.setup_for(MultiByteParam, byte_size=2)
        self.assertEqual(self.cls.to_asm(), "$f0c0")

    def test_three_byte_param(self):
        self.setup_for(MultiByteParam, byte_size=3)

    def test_PointerLabelParam_no_bank(self):
        self.setup_for(PointerLabelParam, bank=None)
        # assuming no label at this location..
        self.assertEqual(self.cls.to_asm(), "$f0c0")
        global all_labels
        # hm.. maybe all_labels should be using a class?
        all_labels = [{"label": "poop", "address": 0xf0c0,
                       "offset": 0xf0c0, "bank": 0,
                       "line_number": 2
                     }]
        self.assertEqual(self.cls.to_asm(), "poop")

class TestPostParsing: #(unittest.TestCase):
    """tests that must be run after parsing all maps"""
    def test_signpost_counts(self):
        self.assertEqual(len(map_names[1][1]["signposts"]), 0)
        self.assertEqual(len(map_names[1][2]["signposts"]), 2)
        self.assertEqual(len(map_names[10][5]["signposts"]), 7)

    def test_warp_counts(self):
        self.assertEqual(map_names[10][5]["warp_count"], 9)
        self.assertEqual(map_names[18][5]["warp_count"], 3)
        self.assertEqual(map_names[15][1]["warp_count"], 2)

    def test_map_sizes(self):
        self.assertEqual(map_names[15][1]["height"], 18)
        self.assertEqual(map_names[15][1]["width"], 10)
        self.assertEqual(map_names[7][1]["height"], 4)
        self.assertEqual(map_names[7][1]["width"], 4)

    def test_map_connection_counts(self):
        self.assertEqual(map_names[7][1]["connections"], 0)
        self.assertEqual(map_names[10][1]["connections"], 12)
        self.assertEqual(map_names[10][2]["connections"], 12)
        self.assertEqual(map_names[11][1]["connections"], 9) # or 13?

    def test_second_map_header_address(self):
        self.assertEqual(map_names[11][1]["second_map_header_address"], 0x9509c)
        self.assertEqual(map_names[1][5]["second_map_header_address"], 0x95bd0)

    def test_event_address(self):
        self.assertEqual(map_names[17][5]["event_address"], 0x194d67)
        self.assertEqual(map_names[23][3]["event_address"], 0x1a9ec9)

    def test_people_event_counts(self):
        self.assertEqual(len(map_names[23][3]["people_events"]), 4)
        self.assertEqual(len(map_names[10][3]["people_events"]), 9)

# run the unit tests when this file is executed directly
if __name__ == "__main__":
    unittest.main()
