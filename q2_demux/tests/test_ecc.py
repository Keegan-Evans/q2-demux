# ----------------------------------------------------------------------------
# Copyright (c) 2016-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import unittest
import numpy as np
import numpy.testing as npt

from q2_demux._ecc import GolayDecoder

golay = GolayDecoder()


class ECCTests(unittest.TestCase):
    def test_golay_module1(self):
        """switching the last base, decode() should recover the original barcode
        """
        sent = golay.encode([0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0])
        rec = sent[:-1] + 'C'  # possible error here
        decoded, errors = golay.decode(rec)
        self.assertEqual(decoded, sent)
        self.assertLess(errors, 1.5)
        rec = sent[:-1] + 'T'  # possible error here
        decoded, errors = golay.decode(rec)
        self.assertEqual(decoded, sent)
        self.assertLess(errors, 1.5)

    def test_golay_matches_old_code(self):
        """ decode should behave as micah's code did, i.e., same golay encoding
        """
        original = 'GCATCGTCAACA'
        rec = 'GCATCGTCCACA'
        corr, nt_errs = golay.decode(rec)
        self.assertEqual(corr, original)
        self.assertEqual(nt_errs, 2)

    def test_decode_bits(self):
        """ decode_bits should have correct num_errs, even if corrected = None
        """
        for bitvec in ten_bitvecs:
            corr, num_errs = golay.decode_bits(bitvec)
            if corr is None:
                self.assertEqual(num_errs, 4)
            else:
                self.assertEqual(((corr + bitvec) % 2).sum(), num_errs)

    def test_decode(self):
        """ decode should decode barcodes from tutorial"""
        barcodes = ['AGCACGAGCCTA',
                    'AACTCGTCGATG',
                    'ACAGACCACTCA',
                    'ACCAGCGACTAG',
                    'AGCAGCACTTGT',
                    'AACTGTGCGTAC',
                    'ACAGAGTCGGCT',
                    'ACCGCAGAGTCA',
                    'ACGGTGAGTGTC', ]
        for bc in barcodes:
            self.assertEqual(golay.decode(bc), (bc, 0))
        for bc in barcodes:
            err_bc = 'C' + bc[1:]
            self.assertEqual(golay.decode(err_bc), (bc, 2))

    def test_decode_length_check(self):
        """ decode should raise if a non 12nt sequence is provided"""
        with self.assertRaisesRegex(ValueError, "length 8nt.$"):
            golay.decode('ACGGTGAG')

    def test_decode_unrecognized_nt(self):
        self.assertEqual(golay.decode('XYZXYZXYZXYZ'), (None, 4))

    def test_G_H(self):
        """ generator and parity check matrices should be s.t. G dot H.T = zeros
        """
        chkmtx = (np.dot(golay.DEFAULT_G, golay.DEFAULT_H.T) % 2)
        self.assertTrue((chkmtx == 0).all())

    def test_another(self):
        """ decode_bits should fix"""
        def _make_12bits():
            n = 12
            res = np.zeros((2 ** n, n), dtype="int")
            for i in range(2 ** n):
                res[i] = tuple((0, 1)[i >> j & 1]
                               for j in range(n - 1, -1, -1))
            return res
        # all possible 12 bit messages
        all_12bits = _make_12bits()

        # test of decode_bits
        trans = np.dot(golay.DEFAULT_G.T, all_12bits[666]) % 2
        err = (
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0)
        rec = (trans + err) % 2
        corr, num_errs = golay.decode_bits(rec)

        npt.assert_equal(corr, trans)
        npt.assert_equal(corr, np.mod(rec + err, 2))
        self.assertEqual(num_errs, 2)

    def test_syndome_LUT(self):
        """default syndrome lookup table should have all syndromes as keys

        also tests other things"""
        syns = []
        errvecs = golay._make_3bit_errors()
        for errvec in errvecs:
            syn = tuple(np.mod(np.dot(errvec, golay.DEFAULT_H.T), 2))
            syns.append(syn)
        self.assertEqual(set(syns), set(golay.DEFAULT_SYNDROME_LUT.keys()))
        self.assertEqual(len(set(syns)), len(syns))
        self.assertEqual(len(syns), len(errvecs))
        self.assertEqual(len(errvecs), 2325)

    def test_make_3bit_errors(self):
        """ 3 bit errors should have all <= 3 bit errs, no >3 bit errors"""
        bitvecs = golay._make_3bit_errors()
        a = list([0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0,
                  0, 0, 0, 0])
        b = list([0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0,
                  0, 1, 0, 0])
        self.assertTrue(a in map(list, bitvecs))
        self.assertFalse(b in map(list, bitvecs))

    def test_golay600_codes(self):
        """ all 600 codes should be left uncorrected, 0 errors"""
        for bc in golay600:
            corr, num_errs = golay.decode(bc)
            self.assertEqual(corr, bc)
            self.assertEqual(num_errs, 0)

    def test_golay600_2bit_errors(self):
        """ A->C, G->T errors should be 2 bit errors for all 600 barcodes """
        for bc in golay600:
            if bc.count('A') == 0:
                continue  # only check those with A's
            err_bc = bc.replace('A', 'C', 1)
            corr, num_errs = golay.decode(err_bc)
            self.assertEqual(corr, bc)
            self.assertEqual(num_errs, 2)

        for bc in golay600:
            if bc.count('G') == 0:
                continue  # only check those with A's
            err_bc = bc.replace('G', 'T', 1)
            corr, num_errs = golay.decode(err_bc)
            self.assertEqual(corr, bc)
            self.assertEqual(num_errs, 2)

    def test_golay600_4bit_errors(self):
        """double A->C, G->T errors should be 2 bit errors for all 600 barcodes
        """
        for bc in golay600:
            if bc.count('A') < 2:
                continue  # only check those with A's
            err_bc = bc.replace('A', 'C', 2)
            corr, num_errs = golay.decode(err_bc)
            self.assertEqual(corr, None)
            self.assertEqual(num_errs, 4)

        for bc in golay600:
            if bc.count('T') < 2:
                continue  # only check those with A's
            err_bc = bc.replace('T', 'G', 2)
            corr, num_errs = golay.decode(err_bc)
            self.assertEqual(corr, None)
            self.assertEqual(num_errs, 4)


# random 24 bit vectors
ten_bitvecs = np.array([
    [0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0,
        1, 0],
    [0, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0,
        0, 1],
    [0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0,
        0, 1],
    [0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1,
        1, 1],
    [1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1,
        0, 1],
    [0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0,
        1, 0],
    [0, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1,
        1, 0],
    [0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0,
        0, 1],
    [0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0,
        1, 1],
    [1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1,
        1, 1]])

golay600_str = """
AACGCACGCTAG
AACTCGTCGATG
AACTGTGCGTAC
AAGAGATGTCGA
AAGCTGCAGTCG
AATCAGTCTCGT
AATCGTGACTCG
ACACACTATGGC
ACACATGTCTAC
ACACGAGCCACA
ACACGGTGTCTA
ACACTAGATCCG
ACACTGTTCATG
ACAGACCACTCA
ACAGAGTCGGCT
ACAGCAGTGGTC
ACAGCTAGCTTG
ACAGTGCTTCAT
ACAGTTGCGCGA
ACATCACTTAGC
ACATGATCGTTC
ACATGTCACGTG
ACATTCAGCGCA
ACCACATACATC
ACCAGACGATGC
ACCAGCGACTAG
ACCGCAGAGTCA
ACCTCGATCAGA
ACCTGTCTCTCT
ACGACGTCTTAG
ACGAGTGCTATC
ACGATGCGACCA
ACGCAACTGCTA
ACGCGATACTGG
ACGCGCAGATAC
ACGCTATCTGGA
ACGCTCATGGAT
ACGGATCGTCAG
ACGGTGAGTGTC
ACGTACTCAGTG
ACGTCTGTAGCA
ACGTGAGAGAAT
ACGTGCCGTAGA
ACGTTAGCACAC
ACTACAGCCTAT
ACTACGTGTGGT
ACTAGCTCCATA
ACTATTGTCACG
ACTCACGGTATG
ACTCAGATACTC
ACTCGATTCGAT
ACTCGCACAGGA
ACTCTTCTAGAG
ACTGACAGCCAT
ACTGATCCTAGT
ACTGTACGCGTA
ACTGTCGAAGCT
ACTGTGACTTCA
ACTTGTAGCAGC
AGAACACGTCTC
AGACCGTCAGAC
AGACGTGCACTG
AGACTGCGTACT
AGAGAGCAAGTG
AGAGCAAGAGCA
AGAGTAGCTAAG
AGAGTCCTGAGC
AGATACACGCGC
AGATCGGCTCGA
AGATCTCTGCAT
AGATGTTCTGCT
AGCACACCTACA
AGCACGAGCCTA
AGCAGCACTTGT
AGCAGTCGCGAT
AGCATATGAGAG
AGCCATACTGAC
AGCGACTGTGCA
AGCGAGCTATCT
AGCGCTGATGTG
AGCGTAGGTCGT
AGCTATCCACGA
AGCTCCATACAG
AGCTCTCAGAGG
AGCTGACTAGTC
AGCTTGACAGCT
AGGACGCACTGT
AGGCTACACGAC
AGGTGTGATCGC
AGTACGCTCGAG
AGTACTGCAGGC
AGTAGTATCCTC
AGTCACATCACT
AGTCCATAGCTG
AGTCTACTCTGA
AGTCTCGCATAT
AGTGAGAGAAGC
AGTGCGATGCGT
AGTGGATGCTCT
AGTGTCACGGTG
AGTGTTCGATCG
AGTTAGTGCGTC
AGTTCAGACGCT
AGTTCTACGTCA
ATAATCTCGTCG
ATACACGTGGCG
ATACAGAGCTCC
ATACGTCTTCGA
ATACTATTGCGC
ATACTCACTCAG
ATAGCTCCATAC
ATAGGCGATCTC
ATATCGCTACTG
ATATGCCAGTGC
ATCACGTAGCGG
ATCACTAGTCAC
ATCAGGCGTGTG
ATCCGATCACAG
ATCCTCAGTAGT
ATCGATCTGTGG
ATCGCGGACGAT
ATCGCTCGAGGA
ATCGTACAACTC
ATCTACTACACG
ATCTCTGGCATA
ATCTGAGCTGGT
ATCTGGTGCTAT
ATCTTAGACTGC
ATGACCATCGTG
ATGACTCATTCG
ATGAGACTCCAC
ATGATCGAGAGA
ATGCACTGGCGA
ATGCAGCTCAGT
ATGCCTGAGCAG
ATGCGTAGTGCG
ATGGATACGCTC
ATGGCAGCTCTA
ATGGCGTGCACA
ATGGTCTACTAC
ATGTACGGCGAC
ATGTCACCGTGA
ATGTGCACGACT
ATGTGTCGACTT
ATTATCGTGCAC
ATTCTGTGAGCG
CAACACGCACGA
CAACTATCAGCT
CAACTCATCGTA
CAAGATCGACTC
CAAGTGAGAGAG
CACACGTGAGCA
CACAGCTCGAAT
CACAGTGGACGT
CACATCTAACAC
CACATTGTGAGC
CACGACAGGCTA
CACGGACTATAC
CACGTCGATGGA
CACGTGACATGT
CACTACTGTTGA
CACTCAACAGAC
CACTCTGATTAG
CACTGGTATATC
CACTGTAGGACG
CAGACATTGCGT
CAGACTCGCAGA
CAGAGGAGCTCT
CAGATACACTTC
CAGATCGGATCG
CAGCACTAAGCG
CAGCATGTGTTG
CAGCGGTGACAT
CAGCTAGAACGC
CAGGTGCTACTA
CAGTACGATCTT
CAGTCACTAACG
CAGTCGAAGCTG
CAGTGATCCTAG
CAGTGCATATGC
CAGTGTCAGGAC
CATACCAGTAGC
CATAGACGTTCG
CATAGCGAGTTC
CATATACTCGCA
CATATCGCAGTT
CATCAGCGTGTA
CATCATGAGGCT
CATCGTATCAAC
CATCTGTAGCGA
CATGAGTGCTAC
CATGCAGACTGT
CATGGCTACACA
CATGTAATGCTC
CATGTCTCTCCG
CATTCGATGACT
CATTGTCTGTGA
CCAGATGATCGT
CCAGTGTATGCA
CCATACATAGCT
CCGACTGAGATG
CCGATGTCAGAT
CCTAGTACTGAT
CCTCTCGTGATC
CGAAGACTGCTG
CGAATCGACACT
CGACAGCTGACA
CGACATGCTATT
CGACTTATGTGT
CGAGAGTTACGC
CGAGCAGCACAT
CGAGGCTCAGTA
CGAGTCTAGTTG
CGAGTTGTAGCG
CGATAGATCTTC
CGATATTCATCG
CGATCGAGTGTT
CGATGCACCAGA
CGATGTCGTCAA
CGCACATGTTAT
CGCACTCTAGAA
CGCAGACAGACT
CGCAGCGGTATA
CGCATGAGGATC
CGCGATAGCAGT
CGCGTAACTGTA
CGCTAGAACGCA
CGCTTATCGAGA
CGGAGTGTCTAT
CGGCGATGTACA
CGTAAGTCTACT
CGTACAGTTATC
CGTACTAGACTG
CGTAGAACGTGC
CGTATCTGCGAA
CGTATGCTGTAT
CGTCAACGATGT
CGTCACGACTAA
CGTCAGACGGAT
CGTCGATCTCTC
CGTGACAATGTC
CGTGATCTCTCC
CGTGCATTATCA
CGTGTACATCAG
CGTGTGATCAGG
CGTTACTAGAGC
CGTTATGTACAC
CGTTCGCATAGA
CTAACGCAGTCA
CTACACAAGCAC
CTACATCTAAGC
CTACGCGTCTCT
CTACTACAGGTG
CTACTGATATCG
CTAGAACGCACT
CTAGAGACTCTT
CTAGCGAACATC
CTAGGTCACTAG
CTAGTCAGCTGA
CTATAGTCGTGT
CTATCAGTGTAC
CTATCTAGCGAG
CTATGCTTGATG
CTCAATGACTCA
CTCAGTATGCAG
CTCATGTACAGT
CTCCACATGAGA
CTCCTACTGTCT
CTCGAGAGTACG
CTCGATTAGATC
CTCGCACATATA
CTCGTGGAGTAG
CTCTCTACCTGT
CTCTGAAGTCTA
CTCTGCTAGCCT
CTGAACGCTAGT
CTGACACGACAG
CTGAGATACGCG
CTGAGCAGAGTC
CTGCAGTACTTA
CTGCTGCGAAGA
CTGGACTCATAG
CTGGAGCATGAC
CTGGCTGTATGA
CTGTATCGTATG
CTGTCTCTCCTA
CTGTGACATTGT
CTGTGGATCGAT
CTGTTCGTAGAG
CTTAGCACATCA
CTTGATGCGTAT
CTTGTGTCGATA
GAACATGATGAG
GAACTGTATCTC
GAAGAGTGATCA
GAAGCTACTGTC
GAAGTCTCGCAT
GAATGATGAGTG
GACACTCGAATC
GACAGCGTTGAC
GACAGGAGATAG
GACAGTTACTGC
GACATCGGCTAT
GACCACTACGAT
GACCGAGCTATG
GACGAGTCAGTC
GACGATATCGCG
GACGCAGTAGCT
GACGCTAGTTCA
GACGTTGCACAG
GACTAACGTCAC
GACTAGACCAGC
GACTCACTCAAT
GACTCGAATCGT
GACTGATCATCT
GACTGCATCTTA
GACTGTCATGCA
GACTTCAGTGTG
GAGAATACGTGA
GAGACAGCTTGC
GAGAGAATGATC
GAGAGCTCTACG
GAGATGCCGACT
GAGCAGATGCCT
GAGCATTCTCTA
GAGCTGGCTGAT
GAGGCTCATCAT
GAGTAGCTCGTG
GAGTATGCAGCC
GAGTCTGAGTCT
GAGTGAGTACAA
GAGTGGTAGAGA
GATACGTCCTGA
GATAGCTGTCTT
GATAGTGCCACT
GATATGCGGCTG
GATCAGAAGATG
GATCCGACACTA
GATCGCAGGTGT
GATCGTCCAGAT
GATCTATCCGAG
GATCTCATAGGC
GATCTTCAGTAC
GATGATCGCCGA
GATGCATGACGC
GATGTCGTGTCA
GATGTGAGCGCT
GATTAGCACTCT
GCAATAGCTGCT
GCACATCGAGCA
GCACGACAACAC
GCACTCGTTAGA
GCACTGAGACGT
GCAGCACGTTGA
GCAGCCGAGTAT
GCAGGATAGATA
GCAGGCAGTACT
GCAGTATCACTG
GCAGTTCATATC
GCATAGTAGCCG
GCATATAGTCTC
GCATCGTCAACA
GCATGTGCATGT
GCATTGCGTGAG
GCCACTGATAGT
GCCAGAGTCGTA
GCCTATACTACA
GCGACTTGTGTA
GCGAGATCCAGT
GCGATATATCGC
GCGGATGTGACT
GCGTACAACTGT
GCGTATCTTGAT
GCGTTACACACA
GCTAAGAGAGTA
GCTAGATGCCAG
GCTAGTCTGAAC
GCTATCACGAGT
GCTATTCGACAT
GCTCAGTGCAGA
GCTCGCTACTTC
GCTGATGAGCTG
GCTGCTGCAATA
GCTGGTATCTGA
GCTGTAGTATGC
GCTGTGTAGGAC
GCTTACATCGAG
GCTTCATAGTGT
GCTTGCGAGACA
GGACGTCACAGT
GGATCGCAGATC
GGCAGTGTATCG
GGCGACATGTAC
GGCGTACTGATG
GGCTATGACATC
GGTATACGCAGC
GGTCACTGACAG
GGTCGTAGCGTA
GGTGCGTGTATG
GTACAAGAGTGA
GTACGGCATACG
GTACTCTAGACT
GTAGACTGCGTG
GTAGAGCTGTTC
GTAGATGCTTCG
GTAGCAACGTCT
GTAGCGCGAGTT
GTAGCTGACGCA
GTAGTGTCTAGC
GTATATCCGCAG
GTATCCATGCGA
GTATGACTGGCT
GTATGCGCTGTA
GTATGTTGCTCA
GTCAACGCGATG
GTCACGACTATT
GTCATATCGTAC
GTCATTCACGAG
GTCCATAGCTAG
GTCGACTCCTCT
GTCGCTGTCTTC
GTCGTAGCCAGA
GTCGTGTGTCAA
GTCTACACACAT
GTCTATCGGAGT
GTCTCATGTAGG
GTCTCTCTACGC
GTCTGACAGTTG
GTCTGGATAGCG
GTCTTCGTCGCT
GTGACCTGATGT
GTGACTGCGGAT
GTGAGGTCGCTA
GTGATAGTGCCG
GTGCAATCGACG
GTGCACATTATC
GTGGCGATACAC
GTGTACCTATCA
GTGTCTACATTG
GTGTGCTATCAG
GTGTGTGTCAGG
GTGTTGCAGCAT
GTTAGAGCACTC
GTTCGCGTATAG
GTTGACGACAGC
GTTGTATACTCG
TAACAGTCGCTG
TAACTCTGATGC
TAAGCGCAGCAC
TACACACATGGC
TACACGATCTAC
TACAGATGGCTC
TACAGTCTCATG
TACATCACCACA
TACCGCTAGTAG
TACGATGACCAC
TACGCGCTGAGA
TACGGTATGTCT
TACGTGTACGTG
TACTAATCTGCG
TACTACATGGTC
TACTGCGACAGT
TACTGGACGCGA
TACTTACTGCAG
TACTTCGCTCGC
TAGACTGTACTC
TAGAGAGAGTGG
TAGATAGCAGGA
TAGATCCTCGAT
TAGCACACCTAT
TAGCATCGTGGT
TAGCCTCTCTGC
TAGCGACATCTG
TAGCGGATCACG
TAGCTCGTAACT
TAGCTGAGTCCA
TAGGTATCTCAC
TAGTCGTCTAGT
TAGTGCTGCGTA
TAGTGTGCTTCA
TAGTTGCGAGTC
TATACGCGCATT
TATCAGGTGTGC
TATCGCGCGATA
TATCTCGAACTG
TATGCACCAGTG
TATGCGAGGTCG
TATGGCACACAC
TATTCGTGTCAG
TCAACAGCATCG
TCAATCTAGCGT
TCACAGATCCGA
TCACGATTAGCG
TCACTATGGTCA
TCACTGGCAGTA
TCACTTCTCGCT
TCAGACAGACCG
TCAGATCCGATG
TCAGCCATGACA
TCAGCTCAACTA
TCAGGACTGTGT
TCAGTACGAGGC
TCAGTCGACGAG
TCAGTGACGTAC
TCATCGCGATAT
TCATCTGACTGA
TCATGGTACACT
TCCACGTCGTCT
TCCAGTGCGAGA
TCCGTCGTCTGT
TCCTAGCAGTGA
TCCTCTGTCGAC
TCCTGAGATACG
TCGAATCACAGC
TCGACTCCTCGT
TCGAGACGCTTA
TCGAGCGAATCT
TCGAGGACTGCA
TCGATACTTGTG
TCGATGAACTCG
TCGCATGAAGTC
TCGCGTATTAGT
TCGCTAGTGAGG
TCGGCTACAGAG
TCGTACGTCATA
TCGTCGATAATC
TCGTGATGTGAC
TCGTGTCTATAG
TCGTTCACATGA
TCTACGGAGAGC
TCTACTCGTAAG
TCTAGCGTAGTG
TCTAGTTAGTCG
TCTCACTAGGTA
TCTCCGCATGTC
TCTCGTAATCAG
TCTCTAGAGCAT
TCTCTCCGTCGA
TCTGAGTCTGAG
TCTGCGTACTAA
TCTGCTAGATGT
TCTGTTGCTCTC
TCTTAGACGACG
TGAACGCTAGCT
TGACATCAGCGG
TGACCATATCGT
TGACGCGATGCA
TGACGGACATCT
TGAGACGTGCTT
TGAGAGAGCATA
TGAGCACACACG
TGAGCGATTCTG
TGAGGATGATAG
TGAGTCACTGGT
TGAGTTCGCTAT
TGATAGTGAGGA
TGATCAGAAGAG
TGATGCTAACTC
TGATGTGTGACC
TGCAGAGCTCAG
TGCATTACGCAT
TGCGCGAATACT
TGCGTATAGTGC
TGCGTCAGTTAG
TGCGTGGTAGAC
TGCTACCATGAG
TGCTAGTCATAC
TGCTATATCTGG
TGCTCAGTATGT
TGCTCGTAGGAT
TGCTCTAGTGGA
TGCTGTGAGCTA
TGGATATGCGCT
TGGCTCTACAGA
TGGTCATCACTA
TGTACACGGCGA
TGTACCGATCAT
TGTCAGTATTCG
TGTCGCTGTAAT
TGTCTTGATAGC
TGTGACTCGTGA
TGTGAGCACGGT
TGTGCAAGCGAC
TGTGCTGTGTAG
TGTGGTACTACG
TGTGTAGCGACT
TGTGTGTGACTT
TGTTATCGCACA
TGTTGACACTAC
TTACTGTGCGAT
TTAGCGTCACGA
TTATCACGTGCA
TTATGCAGTCGT
TTCATGACACTG
TTCGATACTCGA
TTGACAGTCACT
TTGATGCTATGC
TTGCGCATACTA
TTGCGTCAGACA
TTGTATGTGCGT
"""

golay600 = golay600_str.strip().split('\n')
if __name__ == '__main__':
    unittest.main()
