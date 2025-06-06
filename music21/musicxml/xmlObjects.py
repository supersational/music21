# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Name:         musicxml/xmlObjects.py
# Purpose:      MusicXML objects for conversion to and from music21
#
# Authors:      Christopher Ariza
#               Michael Scott Asato Cuthbert
#
# Copyright:    Copyright © 2009-2024 Michael Scott Asato Cuthbert
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
from __future__ import annotations

from collections import OrderedDict
import re

# these single-entity tags are bundled together.
from music21 import articulations
from music21 import exceptions21
from music21 import expressions

DYNAMIC_MARKS = ['p', 'pp', 'ppp', 'pppp', 'ppppp', 'pppppp',
                 'f', 'ff', 'fff', 'ffff', 'fffff', 'ffffff',
                 'mp', 'mf', 'sf', 'sfp', 'sfpp', 'fp', 'rf', 'rfz', 'sfz', 'sffz', 'fz',
                 'n', 'pf', 'sfzp',  # musicxml 3.1
                 'other-dynamics'  # non-empty
                 ]

ARTICULATION_MARKS = OrderedDict(
    [('accent', articulations.Accent),
     ('strong-accent', articulations.StrongAccent),
     ('staccato', articulations.Staccato),
     ('staccatissimo', articulations.Staccatissimo),
     ('spiccato', articulations.Spiccato),
     ('tenuto', articulations.Tenuto),
     ('detached-legato', articulations.DetachedLegato),
     ('scoop', articulations.Scoop),
     ('plop', articulations.Plop),
     ('doit', articulations.Doit),
     ('falloff', articulations.Falloff),
     ('breath-mark', articulations.BreathMark),
     ('caesura', articulations.Caesura),
     ('stress', articulations.Stress),
     ('unstress', articulations.Unstress),
     ('other-articulation', articulations.Articulation),
     ])

# A reversed dictionary mapping class to name, excepting Articulation
# which does not get mapped, and Staccato which must come after Staccatissimo,
# and Accent which must come after StrongAccent
ARTICULATION_MARKS_REV = OrderedDict([(v, k) for k, v in ARTICULATION_MARKS.items()])
del ARTICULATION_MARKS_REV[articulations.Articulation]
del ARTICULATION_MARKS_REV[articulations.Staccato]
del ARTICULATION_MARKS_REV[articulations.Accent]
ARTICULATION_MARKS_REV[articulations.Staccato] = 'staccato'  # py3: move_to_end
ARTICULATION_MARKS_REV[articulations.Accent] = 'accent'  # py3: move_to_end

TECHNICAL_MARKS = OrderedDict([('up-bow', articulations.UpBow),
                               ('down-bow', articulations.DownBow),
                               ('harmonic', articulations.StringHarmonic),
                               ('open-string', articulations.OpenString),
                               ('thumb-position', articulations.StringThumbPosition),
                               ('fingering', articulations.Fingering),
                               ('pluck', articulations.FrettedPluck),
                               ('double-tongue', articulations.DoubleTongue),
                               ('triple-tongue', articulations.TripleTongue),
                               ('stopped', articulations.Stopped),
                               ('snap-pizzicato', articulations.SnapPizzicato),
                               ('string', articulations.StringIndication),
                               # hammer-on and pull-off not implemented because handled
                               # in method objectAttachedSpannersToTechnicals of m21ToXml.py
                               # ('hammer-on', articulations.HammerOn),
                               # ('pull-off', articulations.PullOff),
                               # bend not implemented because it needs many subcomponents
                               # ('bend', articulations.FretBend),
                               ('tap', articulations.FretTap),
                               ('fret', articulations.FretIndication),
                               ('heel', articulations.OrganHeel),
                               ('toe', articulations.OrganToe),
                               ('fingernails', articulations.HarpFingerNails),
                               # TODO: hole
                               # TODO: arrow
                               ('handbell', articulations.HandbellIndication),
                               ('other-technical', articulations.TechnicalIndication),
                               ])
TECHNICAL_MARKS_REV = OrderedDict([(v, k) for k, v in TECHNICAL_MARKS.items()])
# too generic until we have an ordered dict. -- we have that now.  Should we not do it?
del TECHNICAL_MARKS_REV[articulations.TechnicalIndication]
TECHNICAL_MARKS_REV[articulations.Harmonic] = 'harmonic'


# NON-spanner ornaments that go into Expressions
ORNAMENT_MARKS = {'trill-mark': expressions.Trill,
                  'turn': expressions.Turn,
                  'delayed-turn': expressions.Turn,
                  'inverted-turn': expressions.InvertedTurn,
                  'delayed-inverted-turn': expressions.InvertedTurn,
                  # TODO: 'vertical-turn'
                  'shake': expressions.Shake,
                  'mordent': expressions.Mordent,
                  'inverted-mordent': expressions.InvertedMordent,
                  'schleifer': expressions.Schleifer,
                  'other-ornament': expressions.Ornament
                  # TODO: 'accidental-mark' -- something else
                  }

# ------------------------------------------------------------------------------

class MusicXMLException(exceptions21.Music21Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.measureNumber: str = ''
        self.partName: str = ''

    def __str__(self):
        msg = super().__str__()
        if self.measureNumber or self.partName:
            msg = f'In part ({self.partName}), measure ({self.measureNumber}): ' + msg
        return msg


class MusicXMLExportException(MusicXMLException):
    pass


class MusicXMLImportException(MusicXMLException):
    pass


class MusicXMLWarning(UserWarning):
    pass


# ------------------------------------------------------------------------------
# helpers
STYLE_ATTRIBUTES_YES_NO_TO_BOOL = ('hideObjectOnPrint', )


def yesNoToBoolean(value):
    if value in ('yes', True):
        return True
    else:
        return False


def booleanToYesNo(value):
    '''
    Convert a True, False bool to 'yes' or 'no'

    >>> musicxml.xmlObjects.booleanToYesNo(True)
    'yes'
    >>> musicxml.xmlObjects.booleanToYesNo(False)
    'no'

    anything that evaluates to True becomes 'yes'

    >>> musicxml.xmlObjects.booleanToYesNo(5)
    'yes'

    '''
    if value:  # purposely not "is True"
        return 'yes'
    else:
        return 'no'


def fractionToPercent(value):
    '''
    Turns a fraction into a string percent

    >>> musicxml.xmlObjects.fractionToPercent(0.25)
    '25'

    Only does whole numbers for now:

    >>> musicxml.xmlObjects.fractionToPercent(0.251)
    '25'

    '''
    return str(int(value * 100))


_NCNAME = re.compile(r'^[a-zA-Z_][\w.-]*$')


def isValidXSDID(text):
    '''
    Returns True or False if text is a valid xsd:id, that is, an NCName

    From http://www.datypic.com/sc/xsd/t-xsd_NCName.html:

        The type xsd:NCName represents an XML non-colonized name,
        which is simply a name that does not contain colons. An xsd:NCName value must
        start with either a letter or underscore (_) and may contain only letters,
        digits, underscores (_), hyphens (-), and periods (.). This is equivalent
        to the Name type, except that colons are not permitted.

    >>> musicxml.xmlObjects.isValidXSDID('hel_lo')
    True

    Names cannot begin with digits:

    >>> musicxml.xmlObjects.isValidXSDID('4sad')
    False

    Names must be strings:

    >>> musicxml.xmlObjects.isValidXSDID(12345)
    False

    '''
    if not isinstance(text, str):
        return False

    if not text:
        return False

    if _NCNAME.match(text):
        return True
    else:
        return False


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    import music21
    music21.mainTest()
